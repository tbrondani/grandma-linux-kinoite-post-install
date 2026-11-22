#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run with the translator Python inside `unshare -Urn` (no network)."""
import os
os.environ.update(ARGOS_CHUNK_TYPE='MINISBD',ARGOS_DEVICE_TYPE='cpu',ARGOS_INTRA_THREADS='2',ARGOS_INTER_THREADS='1',ARGOS_COMPUTE_TYPE='int8',OMP_NUM_THREADS='2')
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import resource
import time
start=time.monotonic()
from argostranslate import translate
loaded=time.monotonic()-start
cases=[('pt',lang,'Bom dia. Onde fica a estação de trem?') for lang in ['en','es','fr','de','it']]
cases += [(lang,'pt',text) for lang,text in [('en','Good morning. Where is the train station?'),('es','Buenos días. ¿Dónde está la estación de tren?'),('fr','Bonjour. Où est la gare ?'),('de','Guten Morgen. Wo ist der Bahnhof?'),('it',"Buongiorno. Dove si trova la stazione ferroviaria?")]]
results=[]
for source,target,text in cases:
 start=time.monotonic();output=translate.translate(text,source,target);cold=time.monotonic()-start
 start=time.monotonic();repeat=translate.translate(text,source,target);warm=time.monotonic()-start
 results.append(dict(source=source,target=target,input=text,output=output,first_seconds=round(cold,3),repeat_seconds=round(warm,3),passed=bool(output.strip()) and output!=text and output==repeat))
print(json.dumps(dict(network='isolated with unshare -Urn',import_seconds=round(loaded,3),peak_rss_mib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,1),cases=results),ensure_ascii=False,indent=2))
raise SystemExit(0 if all(r['passed'] for r in results) else 1)
