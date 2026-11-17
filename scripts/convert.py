"""Inspect exports, build a review vault, then convert the approved complete export."""
from __future__ import annotations
import argparse
import collections
import copy
import datetime as dt
import gzip
import json
from pathlib import Path
import re
import sys
import zipfile

from archive_engine import ArchiveBuilder
import build_demo as base

VERSION = '1.0.0'
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = {'name':'DeepSeek','slug':'deepseek','accent':'#3964fe','emoji':'🐋'}
FRAGMENTS = {'REQUEST','RESPONSE','TEMPLATE_RESPONSE','THINK','FILE','TOOL_SEARCH','TOOL_OPEN','TOOL_FIND','CONTENT_RISK','TIP'}


def inventory(root):
    result={}
    for p in sorted(root.rglob('*')):
        if p.is_symlink() or not p.resolve().is_relative_to(root.resolve()):
            raise ValueError('Source links are not supported: '+p.name)
        if p.is_file():result[p.relative_to(root).as_posix()]=base.sha(p.read_bytes())
    return result


def timestamp(value):
    result=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None:raise ValueError('Timestamp has no timezone; establish it before conversion')
    return result


def offset(value):
    if not re.fullmatch(r'[+-]\d\d:\d\d',value):raise ValueError('Use an explicit offset such as +08:00')
    hours,minutes=map(int,value[1:].split(':'))
    if minutes>=60 or hours>14 or (hours==14 and minutes):raise ValueError('Invalid timezone offset')
    return dt.timezone((1 if value[0]=='+' else -1)*dt.timedelta(hours=hours,minutes=minutes))


def load_profile(path=None):
    p=copy.deepcopy(DEFAULT_PROFILE) if path is None else json.loads(Path(path).read_bytes())
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,39}',p.get('slug','')):raise ValueError('Invalid provider slug')
    if not isinstance(p.get('name'),str) or not p['name'].strip() or any(x in p['name'] for x in '\r\n[]<>'):
        raise ValueError('Provider name must be a plain single-line label')
    if not re.fullmatch(r'#[0-9a-fA-F]{6}',p.get('accent','')):raise ValueError('Invalid provider color')
    if p.get('emoji') and (not isinstance(p['emoji'],str) or len(p['emoji'])>12 or any(c in p['emoji'] for c in '\r\n')):
        raise ValueError('Invalid provider emoji')
    if not p.get('emoji'):
        p['icon']=p.get('icon') or 'lucide-sparkles'
        if not re.fullmatch(r'lucide-[a-z0-9-]+',p['icon']):raise ValueError('Invalid Lucide icon name')
    return p


def style(profile):
    css=base.CSS.replace('.deepseek-chat','.ai-chat-history').replace('chat-ai-deepseek','chat-ai-'+profile['slug']).replace('#3964fe',profile['accent'])
    selector=f'.ai-chat-history .callout[data-callout="chat-ai-{profile["slug"]}"]'
    if profile.get('emoji'):
        css=css.replace('content: "🐋"','content: '+json.dumps(profile['emoji'],ensure_ascii=False))
    else:
        css+=f'\n{selector} {{ --callout-icon: {profile["icon"]}; }}\n{selector} > .callout-title > .callout-icon::before {{ content:none; display:none; }}\n{selector} > .callout-title > .callout-icon > svg {{ display:block; }}\n'
    return css


def load_source(source):
    marker=json.loads((source/'manifest.json').read_bytes())
    if marker.get('export_format_version')!=3:raise ValueError('Not a DeepSeek v3 / normalized v3 export; inspect and implement an adapter first')
    index=json.loads((source/'chat_session_index.json').read_bytes())
    ids=[row['id'] for row in index]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate conversation ID in export index')
    if not ids:raise ValueError('Export contains no conversations')
    if any(not isinstance(sid,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,100}',sid) for sid in ids):
        raise ValueError('Unsafe conversation ID; map it in an adapter and retain original ID')
    if set(ids)!={p.stem for p in (source/'chat_sessions').glob('*.json')}:raise ValueError('Index/session ID mismatch')
    sessions={}
    for row in index:
        sid=row['id'];d=json.loads((source/'chat_sessions'/f'{sid}.json').read_bytes())
        if d['id']!=sid:raise ValueError('Session filename/ID mismatch')
        if d.get('title') is not None and not isinstance(d['title'],str):raise ValueError('Invalid title')
        timestamp(d['inserted_at']);timestamp(d['updated_at'])
        mids=[m['id'] for m in d['messages']]
        if len(mids)!=len(set(mids)) or any(type(mid) is not int or mid<0 for mid in mids):raise ValueError('Invalid/duplicate message ID')
        byid={m['id']:m for m in d['messages']}
        for mid,m in byid.items():
            if m['role'] not in {'USER','ASSISTANT'}:raise ValueError('Unsupported message role; map roles explicitly in the adapter')
            timestamp(m['inserted_at'])
            if not isinstance(m['status'],str):raise ValueError('Invalid message status')
            seen=set();cur=mid
            while cur is not None:
                if cur in seen or cur not in byid:raise ValueError('Invalid message parent graph, including historical branch')
                seen.add(cur);cur=byid[cur]['parent_id']
            for f in m['fragments']:
                if f['type'] not in FRAGMENTS:raise ValueError('Unhandled fragment type '+str(f['type']))
                for a in f.get('files',[]):
                    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,100}',a['id']):raise ValueError('Unsafe attachment ID')
                    ep=a.get('export_path')
                    if ep:
                        p=(source/ep).resolve()
                        if not p.is_relative_to(source.resolve()):raise ValueError('Attachment path escapes source')
                        if not p.is_file():raise FileNotFoundError('Declared attachment is absent: '+ep)
        base.main_path(d)
        sessions[sid]=d
    return sessions


def features(d):
    flags=set();_,alt=base.main_path(d)
    if alt:flags.add('history')
    if len(d['messages'])>4:flags.add('multi-turn')
    if not d.get('title'):flags.add('missing-title')
    for m in d['messages']:
        if m['status']!='FINISHED':flags.add('unfinished')
        for f in m['fragments']:
            kind=f['type'];text=f.get('content') or ''
            if kind=='THINK':flags.add('thinking')
            if kind.startswith('TOOL_'):flags.add('search')
            if kind=='TOOL_OPEN' and not f.get('url'):flags.add('null-search')
            if '```' in text or '<html' in text:flags.add('code-html')
            if len(text.splitlines())>=70:flags.add('long-content')
            if '\\[' in text or '\\(' in text or '$$' in text:flags.add('math')
            if re.search(r'^\s*\|.*\|',text,re.M):flags.add('table')
            if base.DATA_URI.search(text):flags.add('embedded-resource')
            for a in f.get('files',[]):flags.add('attachment' if a.get('export_path') else 'missing-attachment')
    return flags


def select_samples(sessions,count=6,explicit=None):
    if count < 1:raise ValueError('Sample count must be positive')
    if explicit:
        selected=list(dict.fromkeys(explicit))
        if any(sid not in sessions for sid in selected):raise ValueError('Unknown requested sample ID')
        return selected
    flags={sid:features(d) for sid,d in sessions.items()};selected=[];covered=set()
    for _ in range(min(count,len(sessions))):
        sid=max((s for s in sessions if s not in selected),key=lambda s:(len(flags[s]-covered),len(flags[s]),-len(sessions[s]['messages']),s))
        selected.append(sid);covered|=flags[sid]
    return selected


def engine_hash():
    names=['scripts/convert.py','scripts/archive_engine.py','scripts/build_demo.py','scripts/verify_vault.py','assets/snippets/deepseek-chat.css','references/vault-format.md']
    return base.sha(base.jdump({n:base.sha((ROOT/n).read_bytes()) for n in names}).encode())


def documents(builder,report,phase,selection):
    records=builder.records;counts={'sessions':len(records),'messages':sum(r['messages'] for r in records),'historical_messages':sum(len(r['alternate_ids']) for r in records),'fragments':len(builder.fragment_audit),'attachment_records':sum(len(r['attachments']) for r in records),'copied_attachments':sum(a['state']=='copied' for r in records for a in r['attachments'])}
    counts['missing_attachments']=counts['attachment_records']-counts['copied_attachments']
    heading='样板审核' if phase=='demo' else '完整对话档案'
    intro=(f"这是从 {report['sessions']} 段源对话中选出的 {len(records)} 段样板。请检查问答、样式、目录、分支、脚注和附件，确认后再转换全量。" if phase=='demo' else f"已转换全部 {len(records)} 段对话。")
    home=f"# {builder.provider_name} · {heading}\n\n{intro}\n\n[[01-对话索引|按时间浏览]] · [[02-格式与维护说明|格式说明]] · [[03-完整性核对报告|核对报告]] · [[04-缺失附件清单|缺失附件]]\n\n"
    home+=f"共 {counts['messages']} 条消息、{counts['historical_messages']} 条历史消息、{counts['copied_attachments']} 个实际附件。另有 {counts['missing_attachments']} 条附件记录在导出中没有文件。\n\n"
    home+='用户气泡右对齐；回答按来源显示图标和标题色。思考、检索、长代码与历史分支默认折叠；消息脚注支持回跳。\n'
    index='# 对话索引\n\n[[00-首页|首页]]\n';month=None
    for item in sorted(records,key=lambda x:(x['created'],x['id']),reverse=True):
        if item['created'][:7]!=month:month=item['created'][:7];index+=f'\n## {month}\n\n'
        index+=f"- {item['created'][:10]} · {base.wiki(item['path'],item['title'])} · {item['messages']} 条消息\n"
    missing='# 缺失附件清单\n\n[[00-首页|首页]]\n\n以下附件的源 export_path 为空，不表示转换器丢失了文件。\n\n'
    for item in records:
        for a in item['attachments']:
            if a['state']!='copied':missing+=f"- {base.wiki(item['path'],item['title'])} · m{a['message_id']} · {base.label(a['name'])} · ID `{a['id']}`\n"
    if not counts['missing_attachments']:missing+='本次范围没有缺失附件记录。\n'
    builder.put('00-首页.md',home);builder.put('01-对话索引.md',index)
    builder.put('02-格式与维护说明.md',(ROOT/'references/vault-format.md').read_text('utf-8'))
    builder.put('04-缺失附件清单.md',missing)
    builder.put('_维护/全量结构统计.json',base.jdump(report))
    builder.put('_维护/会话映射.json',base.jdump({'schema_version':VERSION,'scope':phase,'sessions':records}))
    for name,obj in [('片段处理记录',builder.fragment_audit),('消息处理记录',builder.message_records),('正文转换记录',builder.rendered_parts),('资源映射',builder.assets),('特殊记录',{'exceptions':builder.exceptions,'transforms':dict(builder.transforms)}),('抽样依据',selection)]:builder.put('_维护/'+name+'.json',base.jdump(obj))
    builder.put('_维护/源文件清单.json',base.jdump({'files':builder.source_inventory,'excluded_from_archive':['user.json']}))
    builder.put('03-完整性核对报告.md','# 完整性核对报告\n\n[[00-首页|首页]]\n\n正在等待落盘后的独立核验。\n')
    return counts


def convert(source,dest,phase,*,profile=None,tz='+08:00',count=6,ids=None,reviewed_demo=None,approved=False):
    source,dest=Path(source).resolve(),Path(dest).resolve()
    if source.is_relative_to(dest) or dest.is_relative_to(source):raise ValueError('Source and destination must not overlap')
    if dest.exists() and any(dest.iterdir()):raise ValueError('Destination must be empty; existing notes are preserved')
    if phase not in {'demo','full'}:raise ValueError('Unknown conversion phase')
    base.TZ=offset(tz);profile=load_profile(profile)
    before=inventory(source);sessions=load_source(source)
    marker=json.loads((source/'manifest.json').read_bytes())
    originals=marker.get('original_exports',[])
    if not isinstance(originals,list) or any(not isinstance(n,str) or not n for n in originals):
        raise ValueError('original_exports must be a list of source-relative filenames')
    if len(set(originals))!=len(originals):raise ValueError('Duplicate original export provenance path')
    for name in originals:
        path=(source/name).resolve()
        if Path(name).is_absolute() or not path.is_relative_to(source) or not path.is_file():
            raise ValueError('Invalid original export provenance path')
    if profile['slug']!='deepseek':
        norm=marker.get('normalization')
        if not isinstance(norm,dict) or not norm.get('adapter') or not isinstance(norm.get('field_mapping'),dict) or not marker.get('original_exports'):
            raise ValueError('Other providers require a documented normalized adapter and original exports, not a relabelled native export')
    binding={'source_fingerprint':base.sha(base.jdump(before).encode()),'profile':profile,'timezone_offset':tz,'engine_sha256':engine_hash()}
    if phase=='full':
        if not approved or reviewed_demo is None:raise ValueError('Full conversion requires a reviewed demo and explicit approval')
        demo=Path(reviewed_demo);receipt=json.loads((demo/'_维护/样板审核.json').read_bytes())
        if receipt['binding']!=binding:raise ValueError('Export, style, timezone or converter changed since demo review; build a new demo')
        review_manifest=json.loads((demo/'_维护/生成清单.json').read_bytes())
        for path,digest in review_manifest['files'].items():
            target=(demo/path).resolve()
            if not target.is_relative_to(demo.resolve()):raise ValueError('Review manifest path escapes demo')
            if path.startswith('.obsidian/') and path.endswith('.json'):continue
            if not target.is_file() or base.sha(target.read_bytes())!=digest:raise ValueError('Reviewed demo was modified: '+path)
        selected=sorted(sessions)
    else:selected=select_samples(sessions,count,ids)
    builder=ArchiveBuilder(source,dest);builder.provider_name=profile['name'];builder.provider_slug=profile['slug'];builder.cssclass='ai-chat-history'
    report=builder.analyze()
    if report['index_mismatches'] or report['attachment_size_mismatches']:raise ValueError('Index or attachment metadata mismatch')
    for sid in selected:builder.session(sid)
    selection=[{'id':sid,'features':sorted(features(sessions[sid]))} for sid in selected]
    counts=documents(builder,report,phase,selection)
    builder.put('.obsidian/snippets/ai-chat-history.css',style(profile))
    configs=copy.deepcopy(base.INITIAL_CONFIGS);configs['.obsidian/appearance.json']['enabledCssSnippets']=['ai-chat-history']
    configs['.obsidian/core-plugins.json']=list(dict.fromkeys(configs['.obsidian/core-plugins.json']+['footnotes']))
    configs['.obsidian/types.json']['types'].update({'tags':'tags','aliases':'aliases','cssclasses':'multitext','content_verified':'checkbox','pinned':'checkbox'})
    for path,obj in configs.items():builder.put(path,base.jdump(obj))
    for name in ['manifest.json','chat_session_index.json']:builder.put('_原始数据/_导出信息/'+name+'.gz',gzip.compress((source/name).read_bytes(),mtime=0))
    # Normalized adapters retain exact original export files through an explicit allowlist.
    for name in marker.get('original_exports',[]):
        path=(source/name).resolve()
        if not path.is_relative_to(source) or not path.is_file():raise ValueError('Invalid original export provenance path')
        builder.put('_原始数据/_适配前/'+name+'.gz',gzip.compress(path.read_bytes(),mtime=0))
    accounted={'manifest.json','chat_session_index.json','user.json'}|{f'chat_sessions/{sid}.json' for sid in sessions}|set(marker.get('original_exports',[]))
    for d in sessions.values():
        for m in d['messages']:
            for f in m['fragments']:
                accounted.update(a['export_path'] for a in f.get('files',[]) if a.get('export_path'))
    extras=[]
    if phase=='full':
        for name in sorted(set(before)-accounted):
            archive='_原始数据/_未引用/'+name+'.gz'
            builder.put(archive,gzip.compress((source/name).read_bytes(),mtime=0));extras.append({'source':name,'archive':archive})
    builder.put('_维护/未引用源文件.json',base.jdump(extras))
    builder.put('_维护/样板审核.json',base.jdump({'phase':phase,'binding':binding,'selection':selected,'user_approval_asserted':phase=='full' and approved}))
    if inventory(source)!=before:raise RuntimeError('Source changed during conversion')
    # The new entry point never deletes/replaces existing vault content.
    for path,data in builder.outputs.items():
        target=(dest/path).resolve()
        if not target.is_relative_to(dest):raise ValueError('Output path escapes destination')
    for path,data in builder.outputs.items():
        target=dest/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    manifest={'version':VERSION,'scope':phase,'files':{p:base.sha(b) for p,b in sorted(builder.outputs.items())}}
    manifest_path=dest/'_维护/生成清单.json';manifest_path.write_text(base.jdump(manifest),encoding='utf-8')
    from verify_vault import verify
    result=verify(source,dest)
    (dest/'_维护/完整性核验.json').write_text(base.jdump(result),encoding='utf-8')
    if not result['passed']:raise RuntimeError('Independent verification failed; see output report')
    summary=f"# 完整性核对报告\n\n[[00-首页|首页]] · [[04-缺失附件清单|缺失附件明细]]\n\n独立核验通过。本次为 **{phase}**，范围为 {counts['sessions']} 段会话；源导出共 {len(sessions)} 段。\n\n"
    summary+='\n'.join(f'- {k}: {v}' for k,v in counts.items())+'\n\n'
    summary+='原始会话 JSON 可逐字节还原；消息、分支、片段及实际附件与源数据核对一致。缺失附件仅标注，不补造。\n\n[[ _维护/完整性核验.json|独立核验数据]]\n\n原生 Obsidian 阅读视图需要另外检查；数据核验不等同于视觉验收，也不验证历史回答的事实与代码。\n'
    summary=summary.replace('[[ _维护','[[_维护')
    (dest/'03-完整性核对报告.md').write_text(summary,encoding='utf-8')
    for path in ['03-完整性核对报告.md','_维护/完整性核验.json']:manifest['files'][path]=base.sha((dest/path).read_bytes())
    manifest_path.write_text(base.jdump(manifest),encoding='utf-8')
    return {'phase':phase,'verification':'passed',**counts,'source_sessions':len(sessions),'destination':str(dest)}


def shape(value,depth=0):
    if depth>=5:return type(value).__name__
    if isinstance(value,dict):return {str(k):shape(v,depth+1) for k,v in list(value.items())[:50]}
    if isinstance(value,list):return {'type':'list','length':len(value),'samples':[shape(v,depth+1) for v in value[:3]]}
    return type(value).__name__


def inspect(source):
    source=Path(source);result={'kind':'unknown','json_samples':[]}
    if source.is_dir():
        paths=sorted(source.rglob('*.json'));result['json_file_count']=len(paths)
        if (source/'chat_session_index.json').exists() and (source/'manifest.json').exists():
            sessions=load_source(source);result.update(kind='deepseek-v3-compatible',sessions=len(sessions),recommended_samples=[{'id':sid,'features':sorted(features(sessions[sid]))} for sid in select_samples(sessions)])
        for p in paths[:8]:result['json_samples'].append({'path':p.relative_to(source).as_posix(),'shape':shape(json.loads(p.read_bytes()))})
    elif zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as z:
            result['kind']='zip';result['members']=len(z.infolist())
            for entry in [e for e in z.infolist() if e.filename.endswith('.json') and e.file_size<20_000_000][:8]:result['json_samples'].append({'path':entry.filename,'shape':shape(json.loads(z.read(entry)))})
    elif source.suffix.lower()=='.json':result['json_samples']=[{'path':source.name,'shape':shape(json.loads(source.read_bytes()))}]
    else:result.update(kind='requires-adapter',file=source.name,bytes=source.stat().st_size)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    scan=sub.add_parser('inspect');scan.add_argument('--source',type=Path,required=True);scan.add_argument('--report',type=Path,required=True)
    for mode in ['demo','full']:
        cmd=sub.add_parser(mode);cmd.add_argument('--source',type=Path,required=True);cmd.add_argument('--dest',type=Path,required=True);cmd.add_argument('--profile',type=Path);cmd.add_argument('--timezone-offset',default='+08:00')
        if mode=='demo':cmd.add_argument('--count',type=int,default=6);cmd.add_argument('--id',action='append',dest='ids')
        else:cmd.add_argument('--reviewed-demo',type=Path,required=True);cmd.add_argument('--approved',action='store_true')
    a=p.parse_args()
    if a.command=='inspect':
        result=inspect(a.source);a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(base.jdump(result),encoding='utf-8')
    else:result=convert(a.source,a.dest,a.command,profile=a.profile,tz=a.timezone_offset,count=getattr(a,'count',6),ids=getattr(a,'ids',None),reviewed_demo=getattr(a,'reviewed_demo',None),approved=getattr(a,'approved',False))
    print(base.jdump(result))


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');main()
