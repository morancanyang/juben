import { useCallback, useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { ImageOff, X } from 'lucide-react'
import type { Evidence } from './api'
import { ParticleEngine } from './auth/particleEngine'
import { clamp, smooth, useReducedMotion, visibleClock } from './auth/motion'
import { evidenceImage } from './media/evidence'
import './evidence-viewer.css'

export default function EvidenceViewer({ scriptId, evidence, onClose, returnFocus }: {
  scriptId: string; evidence: Evidence; onClose: () => void; returnFocus?: HTMLElement | null
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  const image = useRef<HTMLImageElement>(null)
  const canvas = useRef<HTMLCanvasElement>(null)
  const closeButton = useRef<HTMLButtonElement>(null)
  const onCloseRef = useRef(onClose)
  const closing = useRef(false)
  const finished = useRef(false)
  const [leaving, setLeaving] = useState(false)
  const [canvasActive, setCanvasActive] = useState(false)
  const [failed, setFailed] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const reduced = useReducedMotion()
  const src = evidenceImage(scriptId, evidence)
  onCloseRef.current = onClose

  const requestClose = useCallback(() => {
    if (closing.current) return
    closing.current = true
    setLeaving(true)
  }, [])
  const finish = useCallback(() => {
    if (finished.current) return
    finished.current = true
    onCloseRef.current()
  }, [])

  useEffect(() => {
    const node = dialog.current!
    const trigger = returnFocus ?? document.activeElement as HTMLElement | null
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    node.showModal()
    closeButton.current?.focus({ preventScroll: true })
    return () => {
      node.close()
      document.body.style.overflow = overflow
      if (trigger?.isConnected) trigger.focus({ preventScroll: true })
    }
  }, [])

  useEffect(() => {
    if (!leaving) return
    const node = dialog.current!
    let engine: ParticleEngine | null = null
    let fallbackStart = 0
    let retainedCanvas = false
    setCanvasActive(false)
    try {
      if (!reduced && loaded && !failed && image.current?.naturalWidth && canvas.current) {
        engine = new ParticleEngine(image.current, matchMedia('(max-width: 760px), (pointer: coarse)').matches, 'scene')
        engine.draw(canvas.current, image.current.getBoundingClientRect(), 0)
        retainedCanvas = true
        setCanvasActive(true)
      }
    } catch { engine?.dispose(); engine = null }
    node.dataset.transition = engine ? 'particles' : reduced ? 'reduced' : 'fallback'
    const stop = visibleClock(ms => {
      const seconds = ms / 1000
      if (engine) {
        try { engine.draw(canvas.current!, image.current!.getBoundingClientRect(), seconds) }
        catch {
          engine.dispose(); engine = null; fallbackStart = seconds
          node.dataset.transition = 'fallback'
        }
      }
      const progress = engine ? clamp(seconds / 3.2) : clamp((seconds - fallbackStart) / .35)
      node.style.setProperty('--evidence-interface', String(1 - smooth(seconds / .35)))
      node.style.setProperty('--evidence-backdrop', String(1 - smooth(engine ? (seconds - 2.3) / .9 : progress)))
      node.style.setProperty('--evidence-image', String(engine ? 1 : 1 - smooth(progress)))
      node.dataset.progress = progress.toFixed(3)
      if (progress >= 1) { finish(); return false }
      return true
    })
    return () => {
      stop(); engine?.dispose()
      if (retainedCanvas && canvas.current) { canvas.current.width = 0; canvas.current.height = 0 }
    }
  }, [leaving, reduced, loaded, failed, finish])

  return createPortal(
    <dialog ref={dialog} className={`evidence-viewer ${leaving ? 'is-leaving' : ''}`}
      aria-labelledby="evidence-image-title" aria-describedby="evidence-image-description"
      data-evidence-id={evidence.id} data-canvas-active={canvasActive}
      onCancel={event => { event.preventDefault(); requestClose() }}>
      <div className="evidence-viewer-backdrop" onClick={requestClose} aria-hidden="true" />
      <article className="evidence-viewer-card">
        <div className="evidence-viewer-media">
          {src && !failed ? <>
            {!loaded && <span className="evidence-image-status" role="status">正在展开证据影像…</span>}
            <img ref={image} src={src} alt={`${evidence.title}：${evidence.description}`}
              onLoad={() => { if (!closing.current) setLoaded(true) }} onError={() => { if (!closing.current) setFailed(true) }} />
            <div className="evidence-atmosphere" aria-hidden="true"><i/><i/><i/><i/><i/><i/><i/><i/></div>
          </> : <div className="evidence-image-status"><ImageOff size={28}/><span>这件证物暂未附带影像</span></div>}
        </div>
        <div className="evidence-viewer-copy">
          <span className="section-kicker">EVIDENCE / {evidence.id.toUpperCase()}</span>
          <h2 id="evidence-image-title">{evidence.title}</h2>
          <p id="evidence-image-description">{evidence.description}</p>
          <small>{evidence.source}<span>{evidence.time}</span></small>
        </div>
        <button ref={closeButton} className="evidence-viewer-close" aria-label="关闭证据图片"
          aria-disabled={leaving} onClick={requestClose}><X size={18}/><span>收起影像</span></button>
      </article>
      <canvas ref={canvas} className="evidence-dissolve-canvas" aria-hidden="true"/>
    </dialog>, document.body,
  )
}
