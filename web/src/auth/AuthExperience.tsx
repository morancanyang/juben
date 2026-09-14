import { useCallback, useEffect, useRef, useState, type PointerEvent } from 'react'
import type { User } from '../api'
import AuthForm from './AuthForm'
import EvidenceScene from './EvidenceScene'
import { ParticleEngine, type DissolveMode } from './particleEngine'
import { clamp, smooth, useReducedMotion, visibleClock } from './motion'
import './auth.css'

type Props = { loading: boolean; bootError: string; onAuthenticated: (user: User) => void; onComplete: () => void }

export default function AuthExperience({ loading, bootError, onAuthenticated, onComplete }: Props) {
  const root = useRef<HTMLDivElement>(null)
  const frame = useRef<HTMLDivElement>(null)
  const subject = useRef<HTMLImageElement>(null)
  const canvas = useRef<HTMLCanvasElement>(null)
  const skip = useRef<HTMLButtonElement>(null)
  const ready = useRef(false)
  const dissolveMode = useRef<DissolveMode>('subject')
  const completed = useRef(false)
  const cancel = useRef<(() => void) | null>(null)
  const callbacks = useRef({ onAuthenticated, onComplete })
  callbacks.current = { onAuthenticated, onComplete }
  const [success, setSuccess] = useState(false)
  const [canvasActive, setCanvasActive] = useState(false)
  const reduced = useReducedMotion()
  const [hidden, setHidden] = useState(document.hidden)
  const onReady = useCallback((value: boolean, mode: DissolveMode) => { ready.current = value; dissolveMode.current = mode }, [])
  const finish = useCallback(() => {
    if (completed.current) return
    completed.current = true; cancel.current?.()
    callbacks.current.onComplete()
  }, [])

  useEffect(() => {
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const visibility = () => setHidden(document.hidden)
    document.addEventListener('visibilitychange', visibility)
    return () => { document.body.style.overflow = previous; document.removeEventListener('visibilitychange', visibility) }
  }, [])

  const authenticated = (user: User) => {
    if (success || completed.current) return
    if (frame.current && root.current) {
      const transform = new DOMMatrixReadOnly(getComputedStyle(frame.current).transform)
      root.current.style.setProperty('--pan-x', `${transform.m41}px`)
      root.current.style.setProperty('--pan-y', `${transform.m42}px`)
    }
    callbacks.current.onAuthenticated(user)
    setSuccess(true)
  }

  useEffect(() => {
    if (!success) return
    skip.current?.focus({ preventScroll: true })
    let engine: ParticleEngine | null = null
    let disposed = false
    let fallbackStart = 0
    const node = root.current!
    const initialScroll = node.scrollTop
    setCanvasActive(false)
    try {
      if (!reduced && ready.current && subject.current?.complete && canvas.current && frame.current) {
        engine = new ParticleEngine(subject.current, matchMedia('(max-width: 760px), (pointer: coarse)').matches, dissolveMode.current)
        engine.draw(canvas.current, frame.current.getBoundingClientRect(), 0)
        setCanvasActive(true)
      }
    } catch { engine?.dispose(); engine = null; setCanvasActive(false) }
    node.dataset.transition = engine ? 'particles' : reduced ? 'reduced' : 'fallback'
    node.dataset.dissolveMode = dissolveMode.current
    const stop = visibleClock(ms => {
      const seconds = ms / 1000
      // Once input has ended, bring a scrolled phone scene gently back into view.
      // The canvas reads the new rect each frame, so image and dust remain aligned.
      if (engine && initialScroll > 0) node.scrollTop = initialScroll * (1 - smooth(seconds / .4))
      let progress = clamp((seconds - fallbackStart) / .55)
      if (engine) {
        progress = clamp(seconds / 3.2)
        try {
          node.style.setProperty('--camera-zoom', String(1 + smooth(seconds / 3.2) * .035))
          engine.draw(canvas.current!, frame.current!.getBoundingClientRect(), seconds)
        } catch {
          engine.dispose(); engine = null; fallbackStart = seconds
          setCanvasActive(false); node.dataset.transition = 'fallback'; progress = 0
        }
      }
      node.style.setProperty('--form-opacity', String(1 - smooth(seconds / .4)))
      node.style.setProperty('--scene-opacity', String(1 - smooth(engine ? (seconds - 2.4) / .8 : progress)))
      node.style.setProperty('--success-opacity', String(engine ? 1 - smooth((seconds - 2.4) / .5) : 1 - smooth(progress)))
      node.dataset.progress = progress.toFixed(3)
      if (progress >= 1) { finish(); return false }
      return true
    })
    const cleanup = () => {
      if (disposed) return
      disposed = true; stop(); engine?.dispose()
      if (canvas.current) { canvas.current.width = 0; canvas.current.height = 0 }
    }
    cancel.current = cleanup
    return cleanup
  }, [success, reduced, finish])

  const pointer = (event: PointerEvent) => {
    if (success || reduced || event.pointerType !== 'mouse' || innerWidth <= 760 || root.current?.querySelector('form:focus-within')) return
    root.current?.style.setProperty('--pan-x', `${(event.clientX / innerWidth - .5) * 7}px`)
    root.current?.style.setProperty('--pan-y', `${(event.clientY / innerHeight - .5) * 5}px`)
  }
  return <div className="cinema-gate" ref={root} data-success={success} data-paused={hidden} data-reduced={reduced}
    onPointerMove={pointer} onKeyDown={e => { if (e.key === 'Escape' && success) finish() }}>
    <div className="cinema-backdrop"/>
    <div className="cinema-set">
      <header className="cinema-header"><div className="cinema-brand"><span className="cinema-brand-seal" aria-hidden="true">卷</span><div><h1>夜半卷宗</h1><span>MIDNIGHT CASEBOOK</span></div></div>
        <span className="cinema-header-note"><i/><span className="cinema-room-name">深夜调查室</span><span className="cinema-header-divider"> / </span><span className="cinema-game-kind">单人 AI 剧本杀</span></span></header>
      <div className="cinema-composition">
        <div className="cinema-left"><div className="cinema-opening-line"><span>每一个细节，都曾在场。</span><span>PROLOGUE / 序章</span></div>
          <EvidenceScene frameRef={frame} imageRef={subject} canvasActive={canvasActive} onReady={onReady}/>
          <p className="cinema-quote">有些真相，<br/>藏在消失之前。</p>
        </div>
        <section className="cinema-form-panel" inert={success} aria-hidden={success}>
          {bootError ? <div className="cinema-connection"><span className="cinema-eyebrow">CONNECTION / 连接</span><h2>调查室暂未就绪</h2><p role="alert">{bootError}</p><button className="cinema-submit" onClick={() => location.reload()}>重试连接 <span>↗</span></button></div> :
            <><AuthForm disabled={loading} success={success} onAuthenticated={authenticated}/>{loading && <p className="cinema-restoring" role="status">正在核验已有档案…</p>}</>}
        </section>
      </div>
      <footer className="cinema-footer"><span>一人入局 · 万象藏疑</span><span>KEEP THE EVIDENCE. FIND THE TRUTH.</span><span>夜半 / 卷宗室</span></footer>
    </div>
    <div className="cinema-film" aria-hidden="true"/>
    {success && <><canvas className="cinema-particles" ref={canvas} aria-hidden="true" style={{visibility:canvasActive?'visible':'hidden'}}/>
      <p className="cinema-success" role="status">身份已确认，卷宗正在开启。</p>
      <button className="cinema-skip" ref={skip} onClick={finish}>跳过动画 <span aria-hidden="true">↗</span></button></>}
  </div>
}
