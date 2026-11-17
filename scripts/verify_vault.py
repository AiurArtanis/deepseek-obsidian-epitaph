"""Read-only independent source-to-vault audit. Python standard library only."""
from __future__ import annotations
import argparse
import collections
import datetime as dt
import gzip
import hashlib
import json
import pathlib
import re
import sys


def sha(data): return hashlib.sha256(data).hexdigest()
def load(path): return json.loads(path.read_bytes())
def canonical(obj): return (json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode()


def verify(source, vault):
    failures=[]
    def check(ok, description):
        if not ok: failures.append(description)
    index=load(source/'chat_session_index.json')
    mapping_doc=load(vault/'_维护/会话映射.json')
    mapping=mapping_doc['sessions']
    scope=mapping_doc['scope']
    review=load(vault/'_维护/样板审核.json')
    records={x['id']:x for x in mapping}
    source_ids={x['id'] for x in index}
    check(len(records)==len(mapping),'session counts/duplicates')
    if scope=='full':check(len(records)==len(index),'full session count')
    check(set(records)==set(review['selection']),'selected session coverage')
    check(set(records).issubset(source_ids),'session IDs belong to export')
    check(source_ids=={x.stem for x in (source/'chat_sessions').glob('*.json')},'source session ID coverage')
    if scope=='full':check(set(records)==source_ids,'full session ID coverage')
    note_paths=[x['path'] for x in mapping]
    check(len(set(p.casefold() for p in note_paths))==len(note_paths),'case-insensitive note collisions')
    actual_notes={p.relative_to(vault).as_posix() for p in vault.glob('20??-??/20??-??-??/*.md')}
    check(actual_notes==set(note_paths),'dated note coverage')
    fragments=load(vault/'_维护/片段处理记录.json')
    messages=load(vault/'_维护/消息处理记录.json')
    fragment_by_key={(x['session_id'],x['message_id'],x['fragment']):x for x in fragments}
    message_by_key={(x['session_id'],x['message_id']):x for x in messages}
    check(len(fragment_by_key)==len(fragments),'duplicate audited fragment')
    check(len(message_by_key)==len(messages),'duplicate audited message')
    totals=collections.Counter(); statuses=collections.Counter(); types=collections.Counter()
    copied_sources=set(); expected_fragment_keys=set(); expected_message_keys=set(); source_index={x['id']:x for x in index}
    removed={'created_utc','updated_utc','source_sha256','format_version','sample_focus','archive_note','timezone','type'}
    for sid,rec in records.items():
        data=(source/'chat_sessions'/f'{sid}.json').read_bytes(); d=json.loads(data)
        note=(vault/rec['path']).read_text('utf-8')
        fm={k:json.loads(v) for k,v in (line.split(': ',1) for line in note.split('---',2)[1].strip().splitlines())}
        check(fm['conversation_id']==sid and fm['title']==(d.get('title') or '未命名对话'),sid+': metadata identity')
        check(not removed.intersection(fm),sid+': removed properties')
        check(gzip.decompress((vault/rec['raw']).read_bytes())==data,sid+': raw bytes')
        check(sha(data)==rec['source_sha256'],sid+': source hash')
        check(all(d[k]==source_index[sid][k] for k in ['id','title','pinned','inserted_at','updated_at']),sid+': export index metadata')
        check(len(d['messages'])==source_index[sid]['message_count'],sid+': export index message count')
        byid={m['id']:m for m in d['messages']}
        check(len(byid)==len(d['messages']),sid+': duplicate source message ID')
        # Verify every ancestry chain, including branches that are not in current_message_id.
        for mid in byid:
            seen=set(); cur=mid
            while cur is not None:
                if cur in seen or cur not in byid:
                    failures.append(sid+': invalid parent graph'); break
                seen.add(cur);cur=byid[cur]['parent_id']
        chain=[];cur=d['current_message_id'];seen=set()
        while cur is not None and cur not in seen and cur in byid:
            chain.append(cur);seen.add(cur);cur=byid[cur]['parent_id']
        chain.reverse()
        alternate=[m['id'] for m in d['messages'] if m['id'] not in seen]
        check(rec['main_ids']==chain and rec['alternate_ids']==alternate,sid+': main/branch mapping')
        check(fm['main_message_count']==len(chain) and fm['alternate_message_count']==len(alternate),sid+': main/branch properties')
        check(fm['message_count']==len(byid),sid+': message property')
        totals['main_messages']+=len(chain);totals['historical_messages']+=len(alternate)
        totals['sessions_with_historical_messages']+=bool(alternate)
        parents=collections.Counter(m['parent_id'] for m in d['messages'])
        totals['branch_sessions']+=any(n>1 for n in parents.values())
        defs=re.findall(r'^\[\^msg-(\d+)\]: (.*)$',note,re.M)
        check(collections.Counter(int(mid) for mid,_ in defs)==collections.Counter(byid.keys()),sid+': footnote definitions')
        foot_defs={int(mid):text for mid,text in defs}
        chunks={}; lines=note.splitlines(); i=0
        while i<len(lines):
            found=re.match(r'^> \[!chat-(?:user|ai-[a-z0-9-]+)\].*\[\^msg-(\d+)\]$',lines[i])
            if not found:i+=1;continue
            mid=int(found[1]);chunk=[]
            while i<len(lines) and lines[i].startswith('>'):
                chunk.append(lines[i]);i+=1
            check(mid not in chunks,sid+': duplicate rendered message')
            chunks[mid]='\n'.join(chunk)
        check(set(chunks)==set(byid),sid+': rendered message coverage')
        check(not re.search(r'^\^msg-\d+$',note,re.M),sid+': obsolete block IDs')
        check(not re.search(r'data:[\w.+-]+/[\w.+-]+;base64,[A-Za-z0-9+/=]+',note),sid+': inline encoded image')
        check(all(len(h)<=40 for h in re.findall(r'^## (第 .*?)$',note,re.M)),sid+': round title length')
        expected_atts=[]
        for m in d['messages']:
            mid=m['id'];key=(sid,mid); expected_message_keys.add(key); totals['messages']+=1;statuses[m['status']]+=1
            audit=message_by_key.get(key,{})
            check(audit.get('parent_id')==m['parent_id'] and audit.get('role')==m['role'] and audit.get('status')==m['status'],sid+f': message m{mid} metadata')
            check(audit.get('historical')==(mid in alternate),sid+f': message m{mid} branch flag')
            check(sha(chunks.get(mid,'').encode())==audit.get('rendered_sha256'),sid+f': message m{mid} rendered hash')
            parent=f"父消息：m{m['parent_id']}" if m['parent_id'] is not None else '父消息：无（会话起点）'
            check(parent in foot_defs.get(mid,''),sid+f': message m{mid} parent footnote')
            for fi,f in enumerate(m['fragments'],1):
                fkey=(sid,mid,fi);expected_fragment_keys.add(fkey);totals['fragments']+=1;types[f['type']]+=1
                fa=fragment_by_key.get(fkey,{})
                check(fa.get('type')==f['type'] and fa.get('source_sha256')==sha(canonical(f)),sid+f': fragment m{mid}/f{fi}')
                if f['type']=='FILE':
                    expected_atts.extend((mid,a) for a in f['files'])
        expected_keys=collections.Counter((mid,a['id']) for mid,a in expected_atts)
        actual_keys=collections.Counter((a['message_id'],a['id']) for a in rec['attachments'])
        check(expected_keys==actual_keys,sid+': attachment reference coverage')
        missing=0
        for mid,a in expected_atts:
            totals['attachment_records']+=1
            matches=[x for x in rec['attachments'] if x['message_id']==mid and x['id']==a['id']]
            if not matches: continue
            out=matches[0]
            check(out['name']==a['file_name'] and out['export_path']==a['export_path'],sid+': attachment metadata')
            ep=a.get('export_path')
            if ep:
                src=source/ep; target=vault/out['path'];copied_sources.add(ep)
                check(src.is_file() and target.is_file(),sid+': missing real attachment')
                if src.is_file() and target.is_file():
                    binary=target.read_bytes()
                    check(binary==src.read_bytes() and len(binary)==a['file_size'],sid+': attachment bytes/size')
                    check(sha(binary)==out['sha256'],sid+': attachment hash')
                check(out['state']=='copied' and out['path'] in note,sid+': attachment link/state')
                totals['copied_attachment_records']+=1
            else:
                check(out['state']=='not-exported' and a['id'] in chunks.get(mid,''),sid+': missing attachment notice')
                missing+=1;totals['source_missing_attachments']+=1
        check(fm['attachment_count']==len(expected_atts) and fm['missing_attachment_count']==missing,sid+': attachment properties')
    check(set(fragment_by_key)==expected_fragment_keys,'all source fragment keys represented')
    check(set(message_by_key)==expected_message_keys,'all source message keys represented')
    inventory=load(vault/'_维护/源文件清单.json')['files']
    current={p.relative_to(source).as_posix():sha(p.read_bytes()) for p in source.rglob('*') if p.is_file()}
    check(inventory==current,'source files unchanged')
    for name in load(source/'manifest.json').get('original_exports',[]):
        archived=vault/'_原始数据/_适配前'/f'{name}.gz'
        check(archived.is_file() and gzip.decompress(archived.read_bytes())==(source/name).read_bytes(),
              name+': pre-adapter original bytes')
    accounted={f'chat_sessions/{sid}.json' for sid in source_ids}|copied_sources|{'manifest.json','chat_session_index.json','user.json'}
    # Unreferenced source files are reported separately; a demo intentionally omits unselected assets.
    if scope=='full':
        extras=load(vault/'_维护/未引用源文件.json')
        for item in extras:
            check(gzip.decompress((vault/item['archive']).read_bytes())==(source/item['source']).read_bytes(),'unreferenced source file bytes')
        accounted.update(item['source'] for item in extras)
        accounted.update(load(source/'manifest.json').get('original_exports',[]))
        check(set(current)==accounted.intersection(set(current)),'unaccounted source file')
    for name in ['manifest.json','chat_session_index.json']:
        check(gzip.decompress((vault/'_原始数据/_导出信息'/f'{name}.gz').read_bytes())==(source/name).read_bytes(),name+': export metadata bytes')
    assets=load(vault/'_维护/资源映射.json')
    for asset in assets:
        path=vault/asset['path']
        check(path.is_file() and sha(path.read_bytes())==asset['sha256'],'generated asset '+asset['path'])
    manifest=load(vault/'_维护/生成清单.json')['files']
    checked=0;configs=[]
    for name,digest in manifest.items():
        path=vault/name
        # Obsidian rewrites its own settings after opening. Note bodies and CSS remain strict.
        if name.startswith('.obsidian/') and name.endswith('.json'):
            if path.exists() and sha(path.read_bytes())!=digest:configs.append(name)
            check(path.is_file(),'missing configuration '+name)
            continue
        check(path.is_file() and sha(path.read_bytes())==digest,'generated file hash '+name)
        checked+=1
    totals['sessions']=len(records);totals['source_files']=len(current);totals['unique_original_attachments']=len(copied_sources)
    return {'passed':not failures,
            'scope':scope,'totals':dict(totals),'status_counts':dict(statuses),'fragment_counts':dict(types),
            'generated_file_hashes_checked':checked,'obsidian_config_changes':configs,'failures':failures,
            'checks':['export index and dated-note coverage','all message parent chains including historical branches',
                      'each message rendered once and SHA256 verified','all fragment source hashes',
                      'one native footnote per message','all original attachments byte-for-byte and metadata sizes',
                      'source missing attachments explicitly marked','raw conversation JSON lossless roundtrip',
                      'source inventory unchanged and no orphan attachment','generated resources and file hashes'],
            'limitation':'Archive integrity does not validate historical facts, source code behavior, or visual rendering.'}


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=pathlib.Path,required=True);p.add_argument('--vault',type=pathlib.Path,required=True);p.add_argument('--report',type=pathlib.Path,required=True)
    a=p.parse_args();result=verify(a.source,a.vault)
    a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(0 if result['passed'] else 1)
