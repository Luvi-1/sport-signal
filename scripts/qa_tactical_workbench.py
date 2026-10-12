"""Optional installed-Chromium smoke/viewport check; no external requests."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1280,'height':1000})
    errors=[];requests=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:requests.append(r.url))
    page.goto('http://127.0.0.1:8765')
    page.get_by_role('button',name='American football',exact=True).click()
    page.wait_for_timeout(200)
    assert page.locator('#context-select option').count()>0, page.locator('#summary-state').inner_text()
    page.locator('#context-select').select_option('1')
    assert page.locator('.bar-row').count()>0
    out=ROOT/'artifacts/tactical/ui';out.mkdir(parents=True,exist_ok=True)
    page.screenshot(path=str(out/'workbench-desktop.png'),full_page=False)
    for sport in ['Soccer','Basketball','Baseball','Tennis']:
        page.get_by_role('button',name=sport,exact=True).click()
        page.wait_for_timeout(100)
        assert page.locator('#sport-name').inner_text()==sport
    page.get_by_role('button',name='Five-sport research synthesis',exact=True).click()
    assert 'Executive finding' in page.locator('#document-text').inner_text()
    page.get_by_role('button',name='Close',exact=True).click()
    page.set_viewport_size({'width':375,'height':900})
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
    page.screenshot(path=str(out/'workbench-mobile.png'),full_page=False)
    assert not errors,errors
    assert all(x.startswith('http://127.0.0.1:8765') for x in requests),requests
    print('PASS: five sport navigation, real conditional-count view, document dialog, mobile width, no JS errors or external requests')
    browser.close()
