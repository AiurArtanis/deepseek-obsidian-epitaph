"""Collect message-local web sources without fetching URLs or executing content."""
from __future__ import annotations

import html
import re
from urllib.parse import quote, urlsplit


def web_url(value):
    if not isinstance(value, str):
        return None
    value = value.strip()
    try:
        parsed = urlsplit(value)
        return value if parsed.scheme.lower() in {'http', 'https'} and parsed.hostname else None
    except ValueError:
        return None


def prose_only(content):
    """Exclude fenced and inline code: example URLs are not answer references."""
    fence = None
    # The archive presents complete raw HTML blocks as source code as well.
    content = re.sub(r'(?ms)^([ \t]*<([A-Za-z][\w:-]*)\b[^\n]*.*?</\2\s*>[ \t]*)(?=\n|$)', '', content or '')
    for line in content.splitlines():
        marker = re.match(r'^\s*(?:>\s*)*(`{3,}|~{3,})', line)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence):
                fence = None
            continue
        if marker:
            fence = marker[1]
            continue
        yield re.sub(r'(`+)(.*?)\1', '', line)


def answer_links(content):
    # Keep labels for ordinary Markdown links, including a parenthesized URL path.
    target = r'(?:<https?://[^>]+>|https?://(?:[^\s()]+|\([^\s()]*\))+)'
    link = re.compile(r'(?<!!)\[((?:\\.|[^\]])*)\]\((' + target + r')(?:\s+["\'][^"\']*["\'])?\)')
    lines=list(prose_only(content));definitions={};body=[]
    key=lambda value:' '.join(value.split()).casefold()
    for line in lines:
        definition=re.match(r'^ {0,3}\[([^\]]+)\]:\s*(<https?://[^>]+>|https?://\S+)',line)
        if definition:
            definitions[key(definition[1])]=definition[2].strip('<>')
        else:
            body.append(line)
    for line in body:
        # Images are already archived as resources, not listed as web pages.
        line = re.sub(r'!\[[^\]]*\]\([^\n]*?\)', '', line)
        line = re.sub(r'!\[[^\]]*\](?:\[[^\]]*\])?', '', line)
        spans = [];candidates=[]
        for match in link.finditer(line):
            candidates.append((match.start(),match[2].strip('<>'),re.sub(r'\\([\[\]_*`])', r'\1', match[1])))
            spans.append(match.span())
        for start, end in reversed(spans):
            line = line[:start] + ' ' * (end - start) + line[end:]
        for match in re.finditer(r'\[([^\]]+)\](?:\[([^\]]*)\])?',line):
            reference=key(match[2] or match[1])
            if reference in definitions:
                candidates.append((match.start(),definitions[reference],match[1]))
        for match in re.finditer(r'https?://[^\s<>"\']+', line):
            value = match[0].rstrip('.,;:!?，。；：！？')
            while value.endswith(')') and value.count(')') > value.count('('):
                value = value[:-1]
            candidates.append((match.start(),value,''))
        for _,url,title in sorted(candidates,key=lambda candidate:candidate[0]):
            yield url,title


def collect_sources(message):
    """First-seen order, exact-URL deduplication, no cross-turn/branch borrowing."""
    if message['role'] != 'ASSISTANT':
        return []
    entries = {}

    def add(url, title='', site_name='', origin=''):
        url = web_url(url)
        if not url:
            return
        clean = lambda v: ' '.join(str(v or '').split())
        entry = entries.setdefault(url, {'url': url, 'title': '', 'site_name': '', 'origins': []})
        if title and not entry['title']:
            entry['title'] = clean(title)
        if site_name and not entry['site_name']:
            entry['site_name'] = clean(site_name)
        if origin not in entry['origins']:
            entry['origins'].append(origin)

    for fragment in message['fragments']:
        kind = fragment['type']
        if kind == 'TOOL_SEARCH':
            for item in fragment.get('results') or []:
                add(item.get('url'), item.get('title'), item.get('site_name'), 'search')
        elif kind == 'TOOL_OPEN':
            add(fragment.get('url'), fragment.get('title'), fragment.get('site_name'), 'open')
        elif kind in {'RESPONSE', 'TEMPLATE_RESPONSE'}:
            for url, title in answer_links(fragment.get('content')):
                add(url, title, origin='answer')
    for entry in entries.values():
        entry['title'] = entry['title'] or urlsplit(entry['url']).hostname
    return list(entries.values())


def escape_label(value):
    return re.sub(r'([\\`*_{}\[\]])', r'\\\1', html.escape(value))


def render_sources(message):
    entries = collect_sources(message)
    if not entries:
        return ''
    lines = ['---', '', f'**参考网页 · {len(entries)} 个**', '',
             '按该条回答的检索记录与正文链接整理。', '']
    for number, entry in enumerate(entries, 1):
        url = quote(entry['url'], safe='/:?=&%#@+~!$;,*-._')
        line = f"{number}. [{escape_label(entry['title'])}](<{url}>)"
        if entry['site_name']:
            line += ' · ' + escape_label(entry['site_name'])
        lines.append(line)
    return '\n'.join(lines)
