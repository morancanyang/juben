"""Independent NPC chats, layout, portraits and irrelevant-question regression."""
import json
import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE=os.environ.get('E2E_BASE_URL','http://127.0.0.1:8770')
OUT=Path(os.environ.get('E2E_OUTPUT_DIR','test-results/dialogue'));OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    ctx=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
    guest=ctx.request.post(BASE+'/api/v1/auth/guest',data={}).json()['user']
    state=ctx.request.post(BASE+'/api/v1/sessions',data={'script_id':'rain-manor','difficulty':'story'},headers={'X-CSRF-Token':guest['csrf'],'Idempotency-Key':'dialogue-audit-start'}).json()['state']
    page=ctx.new_page();page.route('https://fonts.googleapis.com/**',lambda r:r.abort())
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(BASE+'/#play',wait_until='networkidle')
    expect(page.locator('.play-page')).to_be_visible()
    responses=[]
    def ask(text):
        before=len(ctx.request.get(BASE+f"/api/v1/sessions/{state['id']}/state").json()['messages'])
        page.get_by_label('向林晚提问').fill(text);page.get_by_role('button',name='发送问题',exact=True).click()
        deadline=time.monotonic()+15
        while True:
            current=ctx.request.get(BASE+f"/api/v1/sessions/{state['id']}/state").json()
            if len(current['messages'])>before and not current['active_run']:break
            assert time.monotonic()<deadline
            page.wait_for_timeout(150)
        replies=[m['text'] for m in current['messages'][before:] if m['role']=='assistant']
        expect(page.locator('.message-history').get_by_text(replies[-1],exact=True).last).to_be_visible()
        responses.append({'question':text,'reply':replies})
        return replies
    for text in ['你好','为什么天空是蓝色的','你喜欢卡通片吗']:
        assert not any('二十二' in s or '公司' in s for s in ask(text))
    assert any('二十二点二十分' in s for s in ask('你好，案发时你什么时候送茶？'))
    user=page.locator('.message-history .player-message').last.bounding_box()
    npc=page.locator('.message-history .message:not(.player-message)').last.bounding_box()
    assert user['x']>npc['x']
    assert page.locator('.message-history .message:not(.player-message) img').last.evaluate('(img)=>img.complete && img.naturalWidth>0')
    page.get_by_label('向林晚提问').fill('林晚未发送的问题')
    page.locator('.actor-tabs button').filter(has_text='周砚').click()
    expect(page.locator('.message-history .message')).to_have_count(0)
    page.get_by_label('向周砚提问').fill('周砚未发送的问题')
    page.locator('.actor-tabs button').filter(has_text='林晚').click()
    expect(page.get_by_label('向林晚提问')).to_have_value('林晚未发送的问题')
    page.screenshot(path=str(OUT/'npc-chats-fixed.png'),full_page=True)
    assert not errors,errors
    report={'status':'passed','checks':['smalltalk does not return case statements','investigative greeting still selects relevant evidence','player on right, NPC on left','NPC portrait loads in message bubble','separate NPC message histories and unsent input'],'responses':responses,'page_errors':errors}
    (OUT/'dialogue-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False),flush=True)
    ctx.close();browser.close()
