import { useEffect, useState, type RefObject } from 'react'
import { evidenceAssets } from './assets'
import type { DissolveMode } from './particleEngine'

type Props = {
  frameRef: RefObject<HTMLDivElement | null>
  imageRef: RefObject<HTMLImageElement | null>
  canvasActive: boolean
  onReady: (ready: boolean, mode: DissolveMode) => void
}

/** Full scene images dissolve together; aligned legacy cutouts remain supported. */
export default function EvidenceScene({ frameRef, imageRef, canvasActive, onReady }: Props) {
  const [plateLoaded, setPlateLoaded] = useState(false)
  const [subjectLoaded, setSubjectLoaded] = useState(false)
  const [failed, setFailed] = useState(false)
  const [stillFailed, setStillFailed] = useState(false)
  const [stillLoaded, setStillLoaded] = useState(false)
  const still = !stillFailed ? evidenceAssets.still : null
  const layered = !still && !!evidenceAssets.plate && !!evidenceAssets.subject && !failed
  useEffect(() => {
    onReady(still ? stillLoaded : layered && plateLoaded && subjectLoaded, still ? 'scene' : 'subject')
  }, [still, stillLoaded, layered, plateLoaded, subjectLoaded, onReady])
  const missing = !layered && !still
  const fail = () => { setFailed(true); onReady(false, 'subject') }
  return <section className="cinema-evidence" aria-label="夜半卷宗 · 序章桌面影像">
    <div className="cinema-scene-meta"><span>夜半卷宗</span><i/><span>调查室 / 序章</span></div>
    <div className="cinema-camera" ref={frameRef} data-media={still ? 'scene' : layered ? 'subject' : 'missing'}>
      <div className="cinema-room" aria-hidden="true"><div className="cinema-window"/><div className="cinema-beam"/><div className="cinema-desk"/><div className="cinema-dust"/></div>
      {still ? <img ref={imageRef} className="cinema-photo cinema-subject" src={still}
        alt="深色木桌上的破旧证据纸，纸上写着夜半卷宗四个大字，旁边放着一杯咖啡"
        draggable={false} style={{ visibility: canvasActive ? 'hidden' : 'visible' }}
        onLoad={() => { setStillLoaded(true); onReady(true, 'scene') }}
        onError={() => { setStillFailed(true); setStillLoaded(false); onReady(false, 'scene') }}/>
      : layered ? <>
        <img className="cinema-photo cinema-plate" src={evidenceAssets.plate!} alt="深夜调查桌，台灯暖光与模糊的雨窗" draggable={false}
          onLoad={() => { setPlateLoaded(true); onReady(subjectLoaded, 'subject') }} onError={fail}/>
        <img ref={imageRef} className="cinema-photo cinema-subject" src={evidenceAssets.subject!} alt="留有少许红茶的白瓷杯"
          draggable={false} style={{ visibility: canvasActive ? 'hidden' : 'visible' }}
          onLoad={() => { setSubjectLoaded(true); onReady(plateLoaded, 'subject') }} onError={fail}/>
      </> : null}
      {missing && <div className="cinema-missing" role="img" aria-label="证物摄影素材尚未补充，当前展示调查室氛围占位">
        <span className="cinema-corner corner-a"/><span className="cinema-corner corner-b"/>
        <span className="cinema-missing-cross">+</span><span className="cinema-missing-text">现场影像暂缺</span>
        <span className="cinema-missing-caption">旧卷宗 · 一杯咖啡</span>
      </div>}
      {!still && <div className="cinema-evidence-tag"><span>E-01 / 现场采集</span></div>}
    </div>
    <div className="cinema-scene-caption"><span className="cinema-caption-line"/><p>沉默的证物。<br/><span>尚未说完的故事。</span></p><span className="cinema-caption-index">01 — 06</span></div>
  </section>
}
