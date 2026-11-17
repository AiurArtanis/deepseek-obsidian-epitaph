"""End-to-end checks for arbitrary exports, review binding and provider adaptation."""
import copy
import gzip
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from convert import convert,inspect,load_profile,style
from make_synthetic_export import FIXTURE,SAMPLES
from verify_vault import verify


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'source'
        shutil.copytree(FIXTURE,self.source)
        (self.source/'manifest.json').write_text('{"export_format_version":3}')

    def change(self,n,edit):
        path=self.source/'chat_sessions'/f'{SAMPLES[n-1][0]}.json'
        obj=json.loads(path.read_bytes());edit(obj)
        path.write_text(json.dumps(obj,ensure_ascii=False),encoding='utf-8')
        index_path=self.source/'chat_session_index.json';idx=json.loads(index_path.read_bytes())
        for row in idx:
            if row['id']==obj['id']:
                for key in ['title','updated_at','inserted_at','pinned']:row[key]=obj[key]
                row['message_count']=len(obj['messages'])
        index_path.write_text(json.dumps(idx,ensure_ascii=False),encoding='utf-8')

    def test_arbitrary_ids_sample_then_complete(self):
        old=SAMPLES[0][0];new='synthetic-seventh-conversation'
        d=json.loads((self.source/'chat_sessions'/f'{old}.json').read_bytes())
        d['id']=new;d['inserted_at']='2025-06-15T09:10:11Z';d['updated_at']=d['inserted_at']
        (self.source/'chat_sessions'/f'{new}.json').write_text(json.dumps(d),encoding='utf-8')
        ip=self.source/'chat_session_index.json';idx=json.loads(ip.read_bytes())
        row={k:d[k] for k in ['id','title','inserted_at','updated_at','pinned']};row['message_count']=len(d['messages']);idx.append(row);ip.write_text(json.dumps(idx),encoding='utf-8')
        demo=self.root/'demo';full=self.root/'full'
        self.assertEqual(convert(self.source,demo,'demo',count=3)['sessions'],3)
        result=convert(self.source,full,'full',reviewed_demo=demo,approved=True)
        self.assertEqual(result['sessions'],7)
        self.assertEqual(result['messages'],27)
        self.assertTrue(verify(self.source,full)['passed'])

    def test_approval_required_before_any_write(self):
        demo=self.root/'demo';convert(self.source,demo,'demo')
        full=self.root/'full'
        with self.assertRaisesRegex(ValueError,'explicit approval'):convert(self.source,full,'full',reviewed_demo=demo)
        self.assertFalse(full.exists())

    def test_changed_export_invalidates_review(self):
        demo=self.root/'demo';convert(self.source,demo,'demo')
        self.change(1,lambda d:d['messages'][0]['fragments'][0].update(content='Different reviewed input'))
        with self.assertRaisesRegex(ValueError,'changed since demo'):convert(self.source,self.root/'full','full',reviewed_demo=demo,approved=True)

    def test_edited_demo_is_preserved_and_rejected(self):
        demo=self.root/'demo';convert(self.source,demo,'demo')
        home=demo/'00-首页.md';home.write_text('manual review edit',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'was modified'):convert(self.source,self.root/'full','full',reviewed_demo=demo,approved=True)
        self.assertEqual(home.read_text('utf-8'),'manual review edit')

    def test_null_title_search_and_invalid_image_string(self):
        def edit(d):
            d['title']=None
            d['messages'][1]['fragments'].extend([
                {'type':'TOOL_OPEN','url':None,'title':None,'snippet':None,'status':'FAILED'},
                {'type':'RESPONSE','content':'Incomplete example: data:image/svg+xml;base64,abcde'},
            ])
        self.change(1,edit)
        dest=self.root/'demo';convert(self.source,dest,'demo')
        mapping=json.loads((dest/'_维护/会话映射.json').read_bytes())['sessions']
        row=next(r for r in mapping if r['id']==SAMPLES[0][0]);text=(dest/row['path']).read_text('utf-8')
        self.assertEqual(row['title'],'未命名对话')
        self.assertIn('原导出未记录 URL',text);self.assertIn('不完整的内嵌图像编码',text)
        self.assertEqual(gzip.decompress((dest/row['raw']).read_bytes()),(self.source/'chat_sessions'/f"{row['id']}.json").read_bytes())

    def test_alternate_cycle_is_rejected(self):
        def edit(d):
            d['messages'][1]['parent_id']=3;d['messages'][2]['parent_id']=2
        self.change(5,edit)
        with self.assertRaisesRegex(ValueError,'parent graph'):convert(self.source,self.root/'demo','demo')
        self.assertFalse((self.root/'demo').exists())

    def test_existing_destination_and_overlap(self):
        dest=self.root/'keep';dest.mkdir();(dest/'user.md').write_text('keep')
        with self.assertRaisesRegex(ValueError,'must be empty'):convert(self.source,dest,'demo')
        self.assertEqual((dest/'user.md').read_text(),'keep')
        with self.assertRaisesRegex(ValueError,'overlap'):convert(self.source,self.source/'vault','demo')

    def test_provider_requires_normalization_and_falls_back_to_spark(self):
        profile=self.root/'provider.json';profile.write_text(json.dumps({'name':'Example AI','slug':'example-ai','accent':'#7058a3'}))
        with self.assertRaisesRegex(ValueError,'normalized adapter'):convert(self.source,self.root/'bad','demo',profile=profile)
        marker={'export_format_version':3,'normalization':{'adapter':'synthetic adapter','field_mapping':{'body':'fragments[].content'}},'original_exports':['original.json']}
        (self.source/'manifest.json').write_text(json.dumps(marker));original=b'{"synthetic": true, "chats": []}'
        (self.source/'original.json').write_bytes(original)
        dest=self.root/'other';convert(self.source,dest,'demo',profile=profile)
        mapping=json.loads((dest/'_维护/会话映射.json').read_bytes())['sessions']
        text=(dest/mapping[0]['path']).read_text('utf-8');css=(dest/'.obsidian/snippets/ai-chat-history.css').read_text('utf-8')
        self.assertIn('[!chat-ai-example-ai]',text)
        self.assertIn('source: "Example AI"',text);self.assertIn('lucide-sparkles',css)
        self.assertEqual(gzip.decompress((dest/'_原始数据/_适配前/original.json.gz').read_bytes()),original)
        (dest/'_原始数据/_适配前/original.json.gz').write_bytes(gzip.compress(b'changed',mtime=0))
        result=verify(self.source,dest)
        self.assertTrue(any('pre-adapter original bytes' in failure for failure in result['failures']))

    def test_malformed_original_provenance_is_rejected_before_writes(self):
        for value in ['original.json', ['../outside.json'], [5]]:
            with self.subTest(value=value):
                (self.source/'manifest.json').write_text(json.dumps({'export_format_version':3,'original_exports':value}))
                with self.assertRaisesRegex(ValueError,'original_export|provenance'):
                    convert(self.source,self.root/'bad','demo')
                self.assertFalse((self.root/'bad').exists())

    def test_provider_style_change_invalidates_review(self):
        demo=self.root/'demo';convert(self.source,demo,'demo')
        p=self.root/'style.json';p.write_text(json.dumps({'name':'DeepSeek','slug':'deepseek','accent':'#123456','emoji':'🐋'}))
        with self.assertRaisesRegex(ValueError,'changed since demo'):convert(self.source,self.root/'full','full',profile=p,reviewed_demo=demo,approved=True)

    def test_unreferenced_resource_is_preserved_in_full_archive(self):
        payload=b'synthetic orphan resource';(self.source/'orphan.bin').write_bytes(payload)
        demo=self.root/'demo';convert(self.source,demo,'demo')
        full=self.root/'full';convert(self.source,full,'full',reviewed_demo=demo,approved=True)
        self.assertEqual(gzip.decompress((full/'_原始数据/_未引用/orphan.bin.gz').read_bytes()),payload)
        self.assertTrue(verify(self.source,full)['passed'])

    def test_unknown_json_inspection_reports_shape_not_private_text(self):
        src=self.root/'unknown.json';src.write_text(json.dumps({'chats':[{'body':'PRIVATE_SENTINEL','timestamp':123,'attachments':[]}]}))
        result=inspect(src)
        self.assertIn('body',json.dumps(result));self.assertNotIn('PRIVATE_SENTINEL',json.dumps(result))

    def test_tampered_attachment_is_detected_independently(self):
        demo=self.root/'demo';convert(self.source,demo,'demo')
        mapping=json.loads((demo/'_维护/会话映射.json').read_bytes())['sessions']
        asset=next(a for r in mapping for a in r['attachments'] if a['state']=='copied')
        (demo/asset['path']).write_bytes(b'corrupted')
        self.assertFalse(verify(self.source,demo)['passed'])


if __name__=='__main__':unittest.main()
