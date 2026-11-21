#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the offline, self-contained manual from its bilingual source content."""
import argparse
import json
from pathlib import Path
import tempfile

MARKER='<!-- Grandma Linux managed manual -->'


def build(root, destination, language='en'):
    if language not in {'en','pt-BR'}:raise ValueError('Unsupported manual language')
    content={code:json.loads((root/'data/guides'/f'manual.{code}.json').read_text()) for code in ['en','pt-BR']}
    ids=[topic['id'] for topic in content['en']['topics']]
    if len(ids)!=len(set(ids)) or ids!=[topic['id'] for topic in content['pt-BR']['topics']]:
        raise ValueError('Manual languages must have the same unique chapter IDs')
    source=root/'data/manual'
    replacements={'@@LANG@@':language,'@@CSS@@':(source/'style.css').read_text(),
                  '@@JS@@':(source/'app.js').read_text(),
                  '@@CONTENT@@':json.dumps(content,ensure_ascii=False).replace('<','\\u003c')}
    html=(source/'index.html').read_text()
    # Replace only template markers, never marker-like text inside manual content.
    import re
    html=re.sub(r'@@(?:LANG|CSS|JS|CONTENT)@@',lambda match:replacements[match[0]],html)
    if destination.exists() and MARKER not in destination.read_text():
        raise RuntimeError('Refusing to overwrite a personal file: '+str(destination))
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w',dir=destination.parent,delete=False,encoding='utf-8') as stream:
        temporary=Path(stream.name);stream.write(html)
    try:
        temporary.chmod(0o644);temporary.replace(destination)
    finally:temporary.unlink(missing_ok=True)
    return destination


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--lang',choices=['en','pt-BR'],default='en')
    args=parser.parse_args();build(Path(__file__).resolve().parents[1],args.output,args.lang)
