"""Workbench data-loss and content contract regression; use an isolated API."""
import json
import os
import time
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright, expect

BASE=os.environ.get('E2E_BASE_URL','http://127.0.0.1:8770')
OUT=Path(os.environ.get('E2E_OUTPUT_DIR','test-results/editor'))
OUT.mkdir(parents=True,exist_ok=True)

def main():
    checks=[];errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',headless=True)
        ctx=browser.new_context(viewport={'width':1440,'height':1050},reduced_motion='reduce')
        username='qa_'+uuid4().hex[:16];password='Audit_728_password'
        result=ctx.request.post(BASE+'/api/v1/auth/register',data={'username':username,'password':password})
        assert result.ok,result.text()
        user=result.json()['user']
        page=ctx.new_page();page.route('https://fonts.googleapis.com/**',lambda r:r.abort())
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(BASE+'/#editor',wait_until='networkidle')
        expect(page.get_by_label('剧本标题')).to_be_visible()
        def info():page.get_by_role('button',name='基础信息',exact=True).click()
        def raw():
            page.get_by_role('button',name='完整结构',exact=True).click()
            return page.get_by_label('剧本 JSON')
        def quality():
            page.get_by_role('button',name='运行质检',exact=True).click()
            expect(page.get_by_role('heading',name='结构质检通过',exact=True)).to_be_visible()
        def title(value):
            info();page.get_by_label('剧本标题').fill(value)
            page.wait_for_function('(value)=>document.querySelector(".private-drafts small")?.textContent!=="私人草稿已保存"',arg=value)
        def current_id():return page.get_by_label('打开已存版本').input_value()
        def saved_content(did):return ctx.request.get(BASE+f'/api/v1/author/drafts/{did}').json()['content']
        def synced(did,title):
            deadline=time.monotonic()+15
            while saved_content(did)['title']!=title and time.monotonic()<deadline:
                page.wait_for_timeout(200)
            assert saved_content(did)['title']==title
        page.get_by_role('button',name='增加人物',exact=True).click()
        page.get_by_role('button',name='增加证物',exact=True).click()
        quality()
        data=json.loads(raw().input_value());eid=data['evidence'][-1]['id']
        assert any(o['evidence_id']==eid for s in data['scenes'] for o in s['objects'])
        info();page.get_by_role('button',name='减少人物',exact=True).click();page.get_by_role('button',name='减少证物',exact=True).click();quality()
        for _ in range(7):page.get_by_role('button',name='增加人物',exact=True).click()
        assert len(json.loads(raw().input_value())['characters'])==8
        info()
        for _ in range(6):page.get_by_role('button',name='减少人物',exact=True).click()
        page.get_by_role('button',name='减少证物',exact=True).click();quality()
        assert len(json.loads(raw().input_value())['evidence'])==3
        checks.append('count controls validate, respect bounds, and attach evidence to a search object')
        title('快速离开也保留的标题')
        page.get_by_role('button',name='总览',exact=True).click()
        page.get_by_role('button',name='剧本工作台',exact=True).click()
        expect(page.get_by_label('剧本标题')).to_have_value('快速离开也保留的标题')
        text=raw();text.fill('{"title": "未写完的 JSON",')
        page.reload(wait_until='networkidle')
        expect(raw()).to_have_value('{"title": "未写完的 JSON",')
        page.get_by_role('button',name='保存新版本',exact=True).click()
        expect(page.locator('.toast')).to_contain_text('JSON 格式无效')
        data['characters']=data['characters'][:2]
        data['questions'][0]['options']=[{'id':c['id'],'label':c['name']} for c in data['characters']]
        data['title']='JSON 未点应用也能保存'
        raw().fill(json.dumps(data,ensure_ascii=False,indent=2))
        page.get_by_role('button',name='保存新版本',exact=True).click()
        expect(page.locator('.private-drafts')).to_contain_text('私人草稿已保存')
        first=current_id();assert first
        assert saved_content(first)['title']==data['title']
        checks.append('immediate navigation and incomplete JSON survive; save applies valid raw JSON and blocks invalid JSON')
        page.reload(wait_until='networkidle');assert current_id()==first
        title('刷新后继续同步同一草稿')
        synced(first,'刷新后继续同步同一草稿')
        expect(page.locator('.private-drafts')).to_contain_text('私人草稿已保存',timeout=10000)
        assert saved_content(first)['title']=='刷新后继续同步同一草稿', (saved_content(first)['title'],page.locator('.private-drafts').inner_text(),page.get_by_label('剧本标题').input_value())
        data=json.loads(raw().input_value());data['title']='JSON 应用仍连接当前草稿'
        raw().fill(json.dumps(data,ensure_ascii=False,indent=2))
        page.get_by_role('button',name='应用 JSON 修改',exact=True).click()
        synced(first,data['title'])
        expect(page.locator('.private-drafts')).to_contain_text('私人草稿已保存',timeout=10000)
        assert current_id()==first and saved_content(first)['title']==data['title']
        checks.append('selected draft survives refresh and JSON apply; autosave updates same server draft and list title')
        page.get_by_role('button',name='保存新版本',exact=True).click()
        expect(page.get_by_label('打开已存版本')).not_to_have_value(first)
        second=current_id()
        raw().fill('{"title":"第二份未完成')
        page.get_by_label('打开已存版本').select_option(first)
        expect(raw()).not_to_have_value('{"title":"第二份未完成')
        page.get_by_label('打开已存版本').select_option(second)
        expect(raw()).to_have_value('{"title":"第二份未完成')
        checks.append('switching versions preserves each unfinished local draft')
        raw().fill(json.dumps(data,ensure_ascii=False,indent=2));page.get_by_role('button',name='应用 JSON 修改',exact=True).click()
        quality();page.get_by_role('button',name='冻结并试玩',exact=True).click()
        expect(page.locator('.play-page')).to_be_visible(timeout=10000)
        page.get_by_role('button',name='剧本工作台',exact=True).click()
        expect(page.get_by_label('剧本标题')).to_be_visible()
        expect(page.get_by_label('打开已存版本')).not_to_have_value('')
        frozen=current_id();before=saved_content(frozen)
        puts=[]
        page.on('request',lambda req:puts.append(req.url) if req.method=='PUT' and '/author/drafts/' in req.url else None)
        title('冻结后本机继续编辑');page.wait_for_timeout(1600)
        assert not puts,puts
        assert saved_content(frozen)==before
        expect(page.locator('.private-drafts')).to_contain_text('冻结版本')
        page.get_by_role('button',name='保存新版本',exact=True).click()
        expect(page.get_by_label('打开已存版本')).not_to_have_value(frozen)
        latest=current_id();assert saved_content(latest)['title']=='冻结后本机继续编辑'
        checks.append('loading/editing frozen versions never PUTs them; saving branches and preserves frozen content')
        ctx.set_offline(True)
        title('离线编辑后自动重连同步');page.wait_for_timeout(1500)
        ctx.set_offline(False)
        synced(latest,'离线编辑后自动重连同步')
        checks.append('reconnecting automatically retries the selected draft sync')
        ctx.set_offline(True)
        title('离线退出仍保留')
        page.wait_for_timeout(1500)
        ctx.set_offline(False)
        page.once('dialog',lambda d:d.dismiss());page.locator('.profile').click()
        expect(page.locator('.editor-page')).to_be_visible()
        page.once('dialog',lambda d:d.accept());page.locator('.profile').click()
        expect(page.locator('.cinema-gate')).to_be_visible()
        assert page.evaluate('(uid)=>!!localStorage.getItem("casebook_author_"+uid)',user['id'])
        page.locator('#case-username').fill(username);page.locator('#case-password').fill('wrong_password')
        page.locator('.cinema-submit').click();expect(page.get_by_role('alert')).to_be_visible()
        page.locator('#case-password').fill(password);page.locator('.cinema-submit').click()
        expect(page.locator('.cinema-gate')).to_have_count(0,timeout=10000)
        page.get_by_role('button',name='剧本工作台',exact=True).click()
        expect(page.get_by_label('剧本标题')).to_have_value('离线退出仍保留')
        synced(latest,'离线退出仍保留')
        expect(page.locator('.private-drafts')).to_contain_text('私人草稿已保存',timeout=10000)
        assert saved_content(latest)['title']=='离线退出仍保留'
        checks.append('logout cancel/confirm, invalid login and same-account relogin preserve pending local drafts and sync them')
        page.screenshot(path=str(OUT/'editor-fixed-desktop.png'),full_page=True)
        # Same browser, another account: local drafts must not appear there.
        page.once('dialog',lambda d:d.accept());page.locator('.profile').click()
        expect(page.locator('.cinema-gate')).to_be_visible()
        page.get_by_role('button',name='先以游客身份调查',exact=True).click()
        expect(page.locator('.cinema-gate')).to_have_count(0,timeout=10000)
        page.get_by_role('button',name='剧本工作台',exact=True).click()
        expect(page.get_by_label('剧本标题')).to_have_value('展柜里的空位')
        expect(page.locator('.private-drafts')).to_contain_text('还没有服务器草稿')
        page.set_viewport_size({'width':390,'height':844})
        page.screenshot(path=str(OUT/'editor-fixed-mobile.png'),full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        checks.append('separate accounts see separate drafts; editor has no overflow at 390px')
        page.set_viewport_size({'width':1440,'height':1050})
        page.get_by_role('button',name='设置',exact=True).click()
        page.once('dialog',lambda d:d.accept())
        page.get_by_role('button',name='删除账户与存档',exact=True).click()
        expect(page.locator('.cinema-gate')).to_be_visible()
        assert page.evaluate('(uid)=>!!localStorage.getItem("casebook_author_"+uid)',user['id'])
        checks.append('deleting a different account retains the original account local drafts')
        ctx.close();browser.close()
    assert not errors,errors
    report={'status':'passed','checks':checks,'page_errors':errors}
    (OUT/'editor-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
