"""Web source footers stay local to each answer, including historical retries."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_demo import Builder
from convert import convert
from make_synthetic_export import FIXTURE
from verify_vault import verify
from web_sources import collect_sources,render_sources


def message(fragments,mid=2):
    return {'id':mid,'role':'ASSISTANT','parent_id':1,'status':'FINISHED',
            'inserted_at':'2026-01-01T00:00:00Z','fragments':fragments}


class WebSourceTests(unittest.TestCase):
    def test_search_open_and_answer_links_are_ordered_and_deduplicated(self):
        m=message([
            {'type':'TOOL_SEARCH','results':[{'url':'https://example.com/a','title':'First [page]','site_name':'Example'}, {'url':None}]},
            {'type':'TOOL_OPEN','url':'https://example.com/a','title':'Duplicate'},
            {'type':'TOOL_OPEN','url':'https://example.com/b','title':None},
            {'type':'RESPONSE','content':'See [First](https://example.com/a), [Paper](https://example.com/paper_(one)) and <https://example.com/c>.'},
        ])
        sources=collect_sources(m)
        self.assertEqual([s['url'] for s in sources],['https://example.com/a','https://example.com/b','https://example.com/paper_(one)','https://example.com/c'])
        self.assertEqual(sources[0]['origins'],['search','open','answer'])
        footer=render_sources(m)
        self.assertIn(r'[First \[page\]](<https://example.com/a>)',footer)
        self.assertIn('paper_%28one%29',footer)
        self.assertIn('参考网页 · 4 个',footer)

    def test_code_images_thoughts_and_non_web_urls_are_not_web_references(self):
        m=message([
            {'type':'THINK','content':'https://example.com/thought'},
            {'type':'TOOL_OPEN','url':'javascript:alert(1)'},
            {'type':'RESPONSE','content':'`https://example.com/inline`\n```html\n<a href="https://example.com/code">Example</a>\n```\n![plot](https://example.com/plot.png)\nActual https://example.com/page.\n~~~text\nhttps://example.com/unfinished-code'},
        ])
        self.assertEqual([s['url'] for s in collect_sources(m)],['https://example.com/page'])

    def test_each_answer_and_historical_branch_has_its_own_footer(self):
        with tempfile.TemporaryDirectory() as temp:
            builder=Builder(FIXTURE,Path(temp));session={'id':'synthetic-local-sources'}
            for mid,historical in [(2,False),(4,False),(6,True)]:
                m=message([{'type':'RESPONSE','content':f'Answer {mid}.'},{'type':'TOOL_SEARCH','results':[{'url':f'https://example.com/{mid}','title':f'Page {mid}'}]}],mid)
                text=builder.message(m,session,[],historical)
                self.assertIn(f'> 1. [Page {mid}](<https://example.com/{mid}>)',text)
                self.assertGreater(text.index('**参考网页'),text.index(f'Answer {mid}.'))
                self.assertNotIn(f'https://example.com/{mid-2}>',text)

    def test_no_empty_footer_and_no_user_message_footer(self):
        self.assertEqual(render_sources(message([{'type':'RESPONSE','content':'No sources.'}])),'')
        m=message([{'type':'RESPONSE','content':'https://example.com/'}]);m['role']='USER'
        self.assertEqual(render_sources(m),'')

    def test_reference_links_preserve_prose_order_and_exclude_html_and_images(self):
        m=message([{'type':'RESPONSE','content':
            'https://example.com/first then [Second][ref] and [Third](https://example.com/third).\n'
            '![Image][pic]\n[ref]: https://example.com/second\n[pic]: https://example.com/image.png\n'
            '[unused]: https://example.com/unused\n<section>\n<a href="https://example.com/html-example">Example</a>\n</section>'}])
        self.assertEqual([s['url'] for s in collect_sources(m)],['https://example.com/first','https://example.com/second','https://example.com/third'])

    def test_independent_verifier_detects_removed_footer_despite_updated_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            vault=Path(temp)/'vault';convert(FIXTURE,vault,'demo')
            mapping=json.loads((vault/'_维护/会话映射.json').read_bytes())['sessions']
            row=next(r for r in mapping if r['id'].startswith('00000001'))
            path=vault/row['path'];text=path.read_text('utf-8')
            self.assertIn('> **参考网页 · 1 个**',text)
            text=text.replace('> 1. [合成资料页](<https://example.com/craft>) · 示例站点','> 1. [wrong](<https://example.com/wrong>)')
            path.write_text(text,encoding='utf-8')
            audit_path=vault/'_维护/消息处理记录.json';audit=json.loads(audit_path.read_bytes())
            start=text.index('> [!chat-ai-deepseek]');end=text.index('\n\n',start)
            for entry in audit:
                if entry['session_id']==row['id'] and entry['message_id']==2:
                    entry['rendered_sha256']=hashlib.sha256(text[start:end].encode()).hexdigest()
            audit_path.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            manifest_path=vault/'_维护/生成清单.json';manifest=json.loads(manifest_path.read_bytes())
            for changed in [path,audit_path]:
                manifest['files'][changed.relative_to(vault).as_posix()]=hashlib.sha256(changed.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest),encoding='utf-8')
            result=verify(FIXTURE,vault)
            self.assertEqual(len(result['failures']),1,result['failures'])
            self.assertIn('web source coverage/order',result['failures'][0])


if __name__=='__main__':unittest.main()
