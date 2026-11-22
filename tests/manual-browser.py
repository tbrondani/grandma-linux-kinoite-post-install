#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Browser integration test. Playwright is a test dependency, not installed by setup."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from manual import build
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--executable',help='Optional Chromium-compatible browser executable')
parser.add_argument('--output',type=Path,default=root/'test-results/manual-browser')
args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
errors=[];requests=[]
with tempfile.TemporaryDirectory(prefix='grandma-manual-browser-') as folder, sync_playwright() as playwright:
    file=build(root,Path(folder)/'manual.html','pt-BR');profile=Path(folder)/'profile'
    options=dict(headless=True,viewport={'width':1280,'height':900},offline=True,color_scheme='light',args=['--no-sandbox'])
    if args.executable:options['executable_path']=args.executable
    browser=playwright.chromium.launch_persistent_context(str(profile),**options)
    page=browser.pages[0]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.on('request',lambda request:requests.append(request.url))
    page.goto(file.as_uri())
    assert page.locator('html').get_attribute('lang')=='pt-BR'
    assert page.locator('#chapters button').count()==16
    assert page.locator('#previous').is_disabled()
    page.screenshot(path=str(args.output/'light-pt-BR.png'),full_page=True)
    page.locator('#show-favorites').click()
    assert page.locator('#empty-favorites').is_visible()
    page.locator('#show-all').click()
    page.locator('[data-chapter="recover"]').click()
    assert page.locator('#chapter-title').inner_text()=='Recuperar arquivos'
    page.locator('#favorite').click()
    page.locator('#show-favorites').click()
    assert page.locator('#chapters button').count()==1
    page.locator('#language').select_option('en')
    assert page.locator('#chapter-title').inner_text()=='Recover files'
    assert page.locator('#chapters button').count()==1
    page.locator('#theme-toggle').click()
    assert page.locator('html').get_attribute('data-theme')=='dark'
    page.screenshot(path=str(args.output/'dark-en-favorites.png'),full_page=True)
    browser.close()
    browser=playwright.chromium.launch_persistent_context(str(profile),**options)
    page=browser.pages[0];page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(file.as_uri())
    assert page.locator('html').get_attribute('lang')=='en'
    assert page.locator('html').get_attribute('data-theme')=='dark'
    assert page.locator('#chapter-title').inner_text()=='Recover files'
    assert page.locator('#favorite').get_attribute('aria-pressed')=='true'
    page.locator('#favorite').click()
    page.locator('#show-favorites').click()
    assert page.locator('#empty-favorites').is_visible()
    page.locator('#show-all').click()
    page.locator('[data-chapter="shutdown"]').click()
    assert page.locator('#next').is_disabled()
    page.locator('#previous').click()
    assert page.locator('#chapter-title').inner_text()=='Ask for help'
    page.locator('#article').focus();page.keyboard.press('ArrowLeft')
    assert page.locator('#chapter-title').inner_text()=='Update the computer'
    for _ in range(10):page.locator('#larger').click()
    assert page.locator('#larger').is_disabled()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path=str(args.output/'large-text.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path=str(args.output/'narrow-large-text.png'),full_page=True)
    assert not errors,errors
    assert not [url for url in requests if not url.startswith('file:')],requests
    browser.close()
print(json.dumps({'passed':True,'chapters':16,'offline':True,'favorites_persist_after_restart':True,
                  'language_and_theme_persist':True,'text_scale':200,'external_requests':0},indent=2))
