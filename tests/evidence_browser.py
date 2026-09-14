"""Evidence art, discovery, reopening and dissolve regression on an isolated API.

E2E_BASE_URL must point to a test database, never the user's live game.
"""
import json
import os
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from playwright.sync_api import expect, sync_playwright

from api.author_template import make_template
from api.seed_content import make_cases

BASE = os.environ.get('E2E_BASE_URL', 'http://127.0.0.1:8768')
OUT = Path(os.environ.get('E2E_OUTPUT_DIR', 'test-results/evidence'))
OUT.mkdir(parents=True, exist_ok=True)


def player(browser, mobile=False, reduced=False):
    context = browser.new_context(viewport={'width': 390, 'height': 844} if mobile else {'width': 1440, 'height': 1000},
                                  is_mobile=mobile, has_touch=mobile, reduced_motion='reduce' if reduced else 'no-preference',
                                  service_workers='block')
    guest = context.request.post(BASE + '/api/v1/auth/guest', data={}).json()['user']
    context.set_extra_http_headers({'X-CSRF-Token': guest['csrf']})
    page = context.new_page()
    page.route('https://fonts.googleapis.com/**', lambda route: route.abort())
    return context, page, guest


def post(context, path, body):
    response = context.request.post(BASE + '/api/v1' + path, data=body, headers={'Idempotency-Key': str(uuid4())})
    assert response.ok, response.text()
    return response.json()


def act(context, state, **body):
    return post(context, f"/sessions/{state['id']}/actions", {'expected_version': state['version'], **body})['state']


def enter(page, user, state):
    page.goto(BASE, wait_until='networkidle')
    page.evaluate('([uid,sid])=>localStorage.setItem("casebook_active_"+uid,sid)', [user['id'], state['id']])
    page.goto(BASE + '/#play', wait_until='networkidle')
    page.reload(wait_until='networkidle')
    expect(page.locator('.play-page')).to_be_visible()


def state_of(context, sid):
    return context.request.get(BASE + f'/api/v1/sessions/{sid}/state').json()


def image_ready(page, eid):
    dialog = page.locator('dialog.evidence-viewer')
    expect(dialog).to_be_visible()
    expect(dialog).to_have_attribute('data-evidence-id', eid)
    page.wait_for_function('()=>{const img=document.querySelector(".evidence-viewer-media img");return img?.complete&&img.naturalWidth===1600}')
    src = dialog.locator('img').get_attribute('src')
    assert '/assets/' in src and '/src/' not in src, src
    assert page.request.get(BASE + src).status == 200
    return dialog


def close(page, mode='button'):
    if mode == 'escape': page.keyboard.press('Escape')
    elif mode == 'backdrop': page.locator('.evidence-viewer-backdrop').click(position={'x': 3, 'y': 3})
    else: page.get_by_role('button', name='关闭证据图片', exact=True).click()
    expect(page.locator('.evidence-viewer')).to_have_count(0, timeout=10000)


def unlock_all(context, state, case):
    for _ in range(4):
        for scene in list(state['scenes']):
            for obj in scene['objects']:
                if obj['available'] and not obj['searched']:
                    state = act(context, state, type='search', scene_id=scene['id'], object_id=obj['id'])
        for e in list(state['evidence']):
            if not e['analyzed']: state = act(context, state, type='analyze', evidence_id=e['id'])
    for combo in case['combinations']: state = act(context, state, type='combine', evidence_ids=combo['inputs'])
    for trigger in case['triggers']:
        rule = trigger['condition']
        state = act(context, state, type='present', evidence_id=rule['ref'], actor_id=rule['actor'])
    return state


def alpha_count(page):
    return page.evaluate('''()=>{
      const c=document.querySelector('.evidence-dissolve-canvas'),ctx=c.getContext('2d');
      const data=ctx.getImageData(0,0,c.width,c.height).data;let count=0;
      for(let i=3;i<data.length;i+=64)if(data[i]>32)count++;
      return count;
    }''')


def main():
    report = {'checks': [], 'images': [], 'page_errors': []}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=True)
        context, page, user = player(browser)
        page.on('pageerror', lambda e: report['page_errors'].append(str(e)))
        case = next(c for c in make_cases() if c['id'] == 'last-train')
        state = post(context, '/sessions', {'script_id': case['id'], 'difficulty': 'standard'})['state']
        initial_points = state['points']
        enter(page, user, state)
        requests = []
        page.on('request', lambda r: requests.append(r.url) if r.method == 'POST' and r.url.endswith('/actions') else None)
        page.get_by_role('button', name='记者的随身录音笔').click()
        image_ready(page, 'e1')
        state = state_of(context, state['id'])
        assert state['points'] == initial_points - 1
        assert len(requests) == 1
        page.screenshot(path=str(OUT / '01-recorder-open.png'))
        original = page.locator('.evidence-viewer-media img').bounding_box()
        started = perf_counter()
        page.get_by_role('button', name='关闭证据图片', exact=True).click()
        page.wait_for_function('()=>document.querySelector(".evidence-viewer")?.dataset.transition==="particles"')
        canvas = page.locator('.evidence-dissolve-canvas').bounding_box()
        assert canvas['x'] == canvas['y'] == 0 and canvas['width'] == 1440 and canvas['height'] == 1000, canvas
        current = page.locator('.evidence-viewer-media img').bounding_box()
        assert all(abs(original[k]-current[k]) < 1 for k in ['x','y','width','height'])
        early = alpha_count(page)
        page.wait_for_function('()=>Number(document.querySelector(".evidence-viewer")?.dataset.progress)>=.40')
        middle = alpha_count(page)
        page.screenshot(path=str(OUT / '02-recorder-dissolve.png'))
        page.get_by_role('button', name='关闭证据图片', exact=True).dispatch_event('click')
        page.wait_for_function('()=>Number(document.querySelector(".evidence-viewer")?.dataset.progress)>=.80')
        late = alpha_count(page)
        page.screenshot(path=str(OUT / '03-recorder-dust.png'))
        expect(page.locator('.evidence-viewer')).to_have_count(0, timeout=10000)
        elapsed = perf_counter()-started
        assert early > middle > late, (early, middle, late)
        assert elapsed >= 3.1, elapsed
        report['dissolve'] = {'alpha_samples':[early,middle,late], 'seconds':elapsed}
        report['checks'].append('First discovery auto-opens; aligned full-image erosion and surviving dust; repeat close does not reset')
        expect(page.get_by_role('button', name='记者的随身录音笔')).to_be_focused()
        page.get_by_role('button', name='记者的随身录音笔').click()
        image_ready(page,'e1'); close(page,'escape')
        assert len(requests) == 1
        after = state_of(context,state['id'])
        assert after['version'] == state['version'] and after['points'] == state['points']
        page.get_by_role('button', name='证物', exact=True).click()
        page.locator('.evidence-item').filter(has_text='最后一段录音').click()
        image_ready(page,'e1'); close(page,'backdrop')
        report['checks'].append('Collected scene and inventory both reopen; Escape/backdrop close; focus restored; no extra action or cost')
        context.close()

        context,page,user=player(browser,reduced=True)
        page.on('pageerror',lambda e:report['page_errors'].append(str(e)))
        for case in make_cases()+[make_template()]:
            sid=case['id']
            if sid=='museum-example':
                draft=post(context,'/author/drafts',{'content':case})
                sid=post(context,f"/author/drafts/{draft['id']}/freeze",{})['script_id']
            state=post(context,'/sessions',{'script_id':sid,'difficulty':'story'})['state']
            state=unlock_all(context,state,case)
            assert len(state['evidence'])==len(case['evidence'])
            enter(page,user,state)
            page.get_by_role('button',name='证物',exact=True).click()
            for e in state['evidence']:
                page.locator('.evidence-item').filter(has_text=e['title']).click()
                image_ready(page,e['id'])
                report['images'].append(case['id']+'-'+e['id'])
                close(page)
        assert len(report['images'])==27
        report['checks'].append('All 27 built images load through hashed URLs, including hidden/combined evidence and frozen teaching drafts')
        context.close()

        context,page,user=player(browser,mobile=True)
        page.on('pageerror',lambda e:report['page_errors'].append(str(e)))
        state=post(context,'/sessions',{'script_id':'rain-manor','difficulty':'story'})['state']
        enter(page,user,state)
        page.get_by_role('button',name='书桌上的茶杯').click();image_ready(page,'e1')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path=str(OUT/'04-mobile-open.png'))
        page.get_by_role('button',name='关闭证据图片',exact=True).click()
        page.wait_for_function('()=>document.querySelector(".evidence-viewer")?.dataset.transition==="particles"')
        assert page.locator('canvas.evidence-dissolve-canvas').evaluate('(c)=>c.width<=390*1.25+1')
        page.emulate_media(reduced_motion='reduce')
        expect(page.locator('.evidence-viewer')).to_have_count(0,timeout=4000)
        report['checks'].append('390px mobile fits; capped particle canvas; reduced motion enabled mid-animation closes safely')
        # An unavailable bitmap keeps the evidence readable and still permits closing.
        context.close()
        context,page,user=player(browser,mobile=True,reduced=True)
        page.on('pageerror',lambda e:report['page_errors'].append(str(e)))
        page.route('**/assets/rain-manor-e1-*.webp',lambda route:route.fulfill(status=404,body='missing'))
        state=post(context,'/sessions',{'script_id':'rain-manor','difficulty':'story'})['state']
        enter(page,user,state)
        page.get_by_role('button',name='书桌上的茶杯').click()
        expect(page.get_by_text('这件证物暂未附带影像')).to_be_visible()
        expect(page.locator('.evidence-viewer-copy h2')).to_have_text('残留的红茶')
        close(page)
        report['checks'].append('Image failure preserves evidence text and close action')
        context.close();browser.close()
    assert not report['page_errors'],report['page_errors']
    report['status']='passed'
    (OUT/'evidence-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
