"""Real FastAPI auth + cinematic integration, including dev-only alpha fixtures.

Run with a migrated, isolated API on AUTH_TEST_BASE (default 8766), and Vite on
AUTH_LAB_BASE (default 5175). API must allow both origins. No production test bypass.
"""
import json
import os
from pathlib import Path
from time import perf_counter
from uuid import uuid4
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get('AUTH_TEST_BASE', 'http://127.0.0.1:8766')
LAB = os.environ.get('AUTH_LAB_BASE', 'http://127.0.0.1:5175')
OUT = Path(os.environ.get('E2E_OUTPUT_DIR', 'test-results/auth'))
OUT.mkdir(parents=True, exist_ok=True)
checks = []
errors = []


def passed(name):
    checks.append(name)
    print('PASS:', name, flush=True)


def login(page, username, password):
    page.locator('#case-username').fill(username)
    page.locator('#case-password').fill(password)
    page.locator('.cinema-submit').click()


def home(page):
    expect(page.locator('.cinema-gate')).to_have_count(0, timeout=10000)
    expect(page.get_by_role('heading', name='真相不会')).to_be_visible()
    assert page.evaluate('document.activeElement.tagName') == 'MAIN'


def screenshot(page, name):
    page.screenshot(path=str(OUT / (name + '.png')), full_page=True)


def main():
    (OUT / 'auth-report.json').write_text(json.dumps({'status': 'running'}), encoding='utf-8')
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=True)

        def fresh(lab=False, query='', mobile=False, reduced=False):
            context = browser.new_context(
                viewport={'width': 390, 'height': 844} if mobile else {'width': 1440, 'height': 1000},
                is_mobile=mobile, has_touch=mobile, device_scale_factor=2 if mobile else 1,
                reduced_motion='reduce' if reduced else 'no-preference', service_workers='block')
            page = context.new_page()
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.route('https://fonts.googleapis.com/**', lambda route: route.abort())
            if lab:
                def forward(route):
                    response = route.fetch(url=BASE + urlsplit(route.request.url).path)
                    route.fulfill(response=response)
                page.route('**/api/**', forward)
            page.goto((LAB + '/tests/auth-lab.html' if lab else BASE) + query, wait_until='networkidle')
            expect(page.locator('.cinema-submit')).to_be_enabled()
            return context, page

        # Production bundle: real registration, failure, network, login and session restoration.
        context, page = fresh()
        has_scene = page.locator('.cinema-camera').get_attribute('data-media') == 'scene'
        screenshot(page, 'desktop-login')
        page.locator('.cinema-mode').click()
        expect(page.get_by_role('heading', name='建立你的调查档案')).to_be_visible()
        page.wait_for_timeout(450)
        screenshot(page, 'desktop-register')
        username = 'e2e_' + uuid4().hex[:16]
        password = 'Casebook_test_728'
        page.locator('#case-username').fill(username)
        page.locator('#case-password').fill(password)
        page.locator('#case-confirmation').fill('not_matching')
        page.locator('.cinema-submit').click()
        expect(page.get_by_role('alert')).to_contain_text('不一致')
        expect(page.locator('.cinema-gate')).to_have_attribute('data-success', 'false')
        page.get_by_role('button', name='显示密码', exact=True).click()
        expect(page.locator('#case-password')).to_have_attribute('type', 'text')
        page.get_by_role('button', name='隐藏密码', exact=True).click()
        page.locator('#case-confirmation').fill(password)
        page.locator('.cinema-submit').click()
        expect(page.locator('.cinema-gate')).to_have_attribute('data-transition', 'particles' if has_scene else 'fallback')
        if has_scene:
            page.wait_for_timeout(1450)
            expect(page.locator('.app-shell')).to_have_attribute('inert', '')
            screenshot(page, 'actual-scene-dissolve')
        home(page)
        me = context.request.get(BASE + '/api/v1/me').json()['user']
        assert me['username'] == username and not me['guest']
        passed('real registration establishes authenticated cookie; confirmation and password visibility')
        page.reload(wait_until='networkidle')
        home(page)
        passed('existing session enters overview without replay')
        page.once('dialog', lambda dialog: dialog.accept())
        page.locator('.profile').click()
        expect(page.locator('.cinema-submit')).to_be_enabled()
        login(page, username, 'incorrect_password')
        expect(page.get_by_role('alert')).to_be_visible()
        expect(page.locator('.cinema-gate')).to_have_attribute('data-success', 'false')
        expect(page.locator('.cinema-particles')).to_have_count(0)
        screenshot(page, 'login-failure')
        passed('real invalid credentials retain evidence and show server error')
        page.route('**/api/v1/auth/login', lambda route: route.abort('connectionfailed'))
        login(page, username, password)
        expect(page.get_by_role('alert')).to_contain_text('网络连接中断')
        page.unroute('**/api/v1/auth/login')
        passed('network failure is recoverable without animation')
        posts = []
        page.on('request', lambda r: posts.append(r.url) if r.url.endswith('/auth/login') else None)
        page.locator('#case-password').fill(password)
        page.locator('form').evaluate('(form)=>{form.requestSubmit();form.requestSubmit();form.requestSubmit()}')
        home(page)
        assert len(posts) == 1, posts
        passed('real login succeeds; repeated submit makes exactly one POST')
        context.close()

        context, page = fresh(mobile=True)
        assert page.locator('.cinema-gate').evaluate('(el)=>el.scrollWidth <= innerWidth')
        # Capture complete scrollable gate; viewport remains the actual phone size afterward.
        height = page.locator('.cinema-gate').evaluate('(el)=>el.scrollHeight')
        page.set_viewport_size({'width': 390, 'height': height})
        screenshot(page, 'mobile-login')
        page.set_viewport_size({'width': 390, 'height': 844})
        page.locator('.cinema-mode').click()
        page.locator('#case-confirmation').focus()
        page.set_viewport_size({'width': 390, 'height': 470})
        page.locator('#case-confirmation').scroll_into_view_if_needed()
        expect(page.locator('#case-confirmation')).to_be_in_viewport()
        assert page.locator('.cinema-gate').evaluate('(el)=>el.scrollWidth <= innerWidth')
        page.keyboard.press('Tab')
        assert page.evaluate('document.activeElement.classList.contains("cinema-submit")')
        screenshot(page, 'mobile-keyboard-register')
        passed('mobile layout, reduced keyboard viewport, accessible labels and keyboard focus')
        context.close()

        # Explicitly test registration-without-session and malformed login responses.
        context, page = fresh()
        page.route('**/api/v1/auth/register', lambda r: r.fulfill(json={'success': True}))
        page.locator('.cinema-mode').click()
        page.locator('#case-username').fill('new_archive')
        page.locator('#case-password').fill(password)
        page.locator('#case-confirmation').fill(password)
        page.locator('.cinema-submit').click()
        expect(page.get_by_role('status')).to_contain_text('档案已建立')
        expect(page.get_by_role('form', name='登录', exact=True)).to_be_visible()
        expect(page.locator('.cinema-gate')).to_have_attribute('data-success', 'false')
        page.route('**/api/v1/auth/login', lambda r: r.fulfill(json={'success': True}))
        login(page, 'new_archive', password)
        expect(page.get_by_role('alert')).to_contain_text('未建立有效登录会话')
        passed('register without session returns to login; malformed auth success never animates')
        context.close()

        if os.environ.get('AUTH_PRODUCTION_ONLY') == '1':
            assert not errors, errors
            report = {'status': 'passed', 'scope': 'production bundle only; dev fixtures excluded', 'checks': checks, 'page_errors': errors}
            (OUT / 'auth-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps(report, ensure_ascii=False), flush=True)
            browser.close()
            return

        # Same production components, but injected test-only matching plate + RGBA fixture.
        context, page = fresh(lab=True)
        expect(page.locator('.cinema-subject')).to_be_visible()
        before = page.locator('.cinema-camera').bounding_box()
        page.locator('#case-username').fill(username)
        page.locator('#case-password').fill(password)
        page.mouse.move(700, 280)
        after = page.locator('.cinema-camera').bounding_box()
        assert abs(before['x'] - after['x']) < .1, 'parallax moved during input'
        # Hold the actual login response; inspect gate before the response is delivered.
        def delayed_login(route):
            response = route.fetch(url=BASE + '/api/v1/auth/login')
            assert response.status == 200
            expect(page.locator('.cinema-gate')).to_have_attribute('data-success', 'false')
            expect(page.locator('.cinema-particles')).to_have_count(0)
            route.fulfill(response=response)
        page.route('**/api/v1/auth/login', delayed_login)
        started = perf_counter()
        page.locator('.cinema-submit').click()
        expect(page.locator('.cinema-gate')).to_have_attribute('data-transition', 'particles')
        page.wait_for_function('Number(document.querySelector(".cinema-gate")?.dataset.progress) > .48')
        expect(page.locator('.cinema-particles')).to_be_visible()
        screenshot(page, 'particle-fixture-midpoint')
        home(page)
        elapsed = perf_counter() - started
        assert 3.0 <= elapsed <= 6.5, elapsed
        screenshot(page, 'investigation-overview')
        passed(f'real auth gates particles; source stays aligned; full transition {elapsed:.2f}s including request')
        context.close()

        for scenario in ['skip', 'reduced', 'broken-image', 'opaque-image', 'canvas-failure', 'mid-animation-failure', 'mobile-particles']:
            context, page = fresh(lab=True, query='?' + scenario if scenario in ['broken-image', 'opaque-image'] else '',
                                  reduced=scenario == 'reduced', mobile=scenario == 'mobile-particles')
            if scenario == 'canvas-failure':
                page.evaluate('HTMLCanvasElement.prototype.getContext = function(){return null}')
            page.locator('.cinema-guest').click()
            gate = page.locator('.cinema-gate')
            if scenario in ['skip', 'mobile-particles', 'mid-animation-failure']:
                expect(gate).to_have_attribute('data-transition', 'particles')
                if scenario == 'skip':
                    page.locator('.cinema-skip').click()
                elif scenario == 'mid-animation-failure':
                    page.evaluate('HTMLCanvasElement.prototype.getContext = function(){return null}')
                    expect(gate).to_have_attribute('data-transition', 'fallback')
                else:
                    canvas = page.locator('.cinema-particles')
                    assert canvas.evaluate('(el)=>el.width') <= 390 * 1.25 + 1
            else:
                expect(gate).to_have_attribute('data-transition', 'reduced' if scenario == 'reduced' else 'fallback')
            home(page)
            passed(scenario + ' completes once and permits entry')
            context.close()

        # A single opaque photograph now dissolves as a whole, including its text.
        context, page = fresh(lab=True, query='?scene')
        expect(page.locator('.cinema-camera')).to_have_attribute('data-media', 'scene')
        expect(page.locator('.cinema-plate')).to_have_count(0)
        expect(page.locator('.cinema-evidence-tag')).to_have_count(0)
        login(page, username, 'incorrect_password')
        expect(page.get_by_role('alert')).to_be_visible()
        expect(page.locator('.cinema-gate')).to_have_attribute('data-success', 'false')
        expect(page.locator('.cinema-subject')).to_be_visible()
        scene_metrics = page.evaluate('''async () => {
          const {ParticleEngine} = await import('/src/auth/particleEngine.ts');
          const image = document.querySelector('.cinema-subject');
          const engine = new ParticleEngine(image, false, 'scene');
          const canvas = document.createElement('canvas');
          const samples=[];
          for(const t of [0,1.4,3.2]){
            engine.draw(canvas,new DOMRect(0,0,800,700),t);
            const pixels=canvas.getContext('2d').getImageData(0,0,800,700).data;
            let total=0;for(let i=3;i<pixels.length;i+=4)total+=pixels[i];
            samples.push(total);
          }
          engine.dispose();return samples;
        }''')
        assert scene_metrics[0] > scene_metrics[1] > scene_metrics[2] == 0
        login(page, username, password)
        expect(page.locator('.cinema-gate')).to_have_attribute('data-dissolve-mode', 'scene')
        expect(page.locator('.cinema-gate')).to_have_attribute('data-transition', 'particles')
        page.wait_for_function('Number(document.querySelector(".cinema-gate")?.dataset.progress) > .42')
        expect(page.locator('.app-shell')).to_have_attribute('inert', '')
        screenshot(page, 'full-scene-fixture-midpoint')
        home(page)
        passed('opaque full scene and its text dissolve; auth failure retains image; entry waits for completion')
        context.close()
        context, page = fresh(lab=True, query='?scene', reduced=True)
        page.locator('.cinema-guest').click()
        expect(page.locator('.cinema-gate')).to_have_attribute('data-transition', 'reduced')
        home(page)
        passed('full scene respects reduced motion')
        context.close()

        # Deterministic shared progress, colour sampling, no background pixels, zero final residue.
        context, page = fresh(lab=True)
        metrics = page.evaluate('''async () => {
          const {ParticleEngine} = await import('/src/auth/particleEngine.ts');
          const {visibleClock} = await import('/src/auth/motion.ts');
          const image = document.querySelector('.cinema-subject');
          const engine = new ParticleEngine(image, false);
          const canvas = document.createElement('canvas');
          const frame = new DOMRect(0,0,800,700);
          const stats = [];
          for(const t of [0,.4,1.2,1.8,2.4,3.2]){
            engine.draw(canvas,frame,t);
            const ctx=canvas.getContext('2d');
            const data=ctx.getImageData(0,0,canvas.width,canvas.height).data;
            let opaque=0,solid=0;for(let i=3;i<data.length;i+=4){if(data[i]>0)opaque++;if(data[i]>220)solid++;}
            stats.push({t,opaque,solid});
          }
          engine.dispose();
          const start=performance.now();
          const perfEngine=new ParticleEngine(image,true);
          for(let i=0;i<120;i++)perfEngine.draw(canvas,frame,i/120*3.2);
          const frameMs=(performance.now()-start)/120;perfEngine.dispose();
          let ticks=0;
          const stop=visibleClock(()=>{ticks++;return true});
          await new Promise(r=>setTimeout(r,90));
          Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});
          document.dispatchEvent(new Event('visibilitychange'));
          const paused=ticks;await new Promise(r=>setTimeout(r,90));
          const afterPause=ticks;
          Object.defineProperty(document,'hidden',{configurable:true,get:()=>false});
          document.dispatchEvent(new Event('visibilitychange'));
          await new Promise(r=>setTimeout(r,90));
          const resumed=ticks;stop();const stopped=ticks;
          await new Promise(r=>setTimeout(r,90));delete document.hidden;
          return {stats,frameMs,paused,afterPause,resumed,stopped,afterStop:ticks};
        }''')
        stats = metrics['stats']
        print('ENGINE_METRICS',json.dumps(metrics),flush=True)
        assert stats[0]['opaque'] == stats[1]['opaque']
        assert stats[0]['solid'] > stats[2]['solid'] > stats[3]['solid'] > stats[4]['solid']
        # Overlapping semi-transparent dust can make a few pixels opaque again.
        assert stats[4]['solid'] < stats[0]['solid'] * .001
        assert stats[4]['opaque'] > 0, 'dust must outlive the subject'
        assert stats[5]['opaque'] == 0
        assert metrics['paused'] == metrics['afterPause'] < metrics['resumed']
        assert metrics['stopped'] == metrics['afterStop']
        assert metrics['frameMs'] < 40
        passed('deterministic subject erosion, dust tail, hidden-tab pause and clock cleanup')
        context.close()
        context, page = fresh(lab=True)
        page.locator('.cinema-guest').click()
        expect(page.locator('.cinema-gate')).to_have_attribute('data-transition', 'particles')
        page.emulate_media(reduced_motion='reduce')
        expect(page.locator('.cinema-gate')).to_have_attribute('data-transition', 'reduced')
        home(page)
        passed('enabling reduced motion mid-transition cancels particles and finishes safely')
        context.close()
        context, page = fresh(lab=True)
        page.locator('.cinema-guest').click()
        expect(page.locator('.cinema-gate')).to_have_attribute('data-transition', 'particles')
        page.keyboard.press('Escape')
        home(page)
        passed('Escape skips transition with focus restored to overview')
        context.close()
        browser.close()
    assert not errors, errors
    report = {'status': 'passed', 'browser': 'Chrome', 'checks': checks, 'engine_metrics': metrics, 'scene_alpha_samples': scene_metrics,
              'page_errors': errors, 'visual_asset': 'Local Blender render in production; no image API. Lab fixtures remain test-only.' if has_scene else 'Missing: safe fade; lab fixtures are test-only.'}
    (OUT / 'auth-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
