/** Development-only test entry. Vite's production build includes only index.html. */
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from '../src/App'
import { evidenceAssets } from '../src/auth/assets'
import '../src/styles.css'
import '../src/final.css'

// Deliberately geometric, non-photographic fixture: tests alpha/colour alignment,
// never a stand-in for the required photographic deliverable.
const source = document.createElement('canvas')
source.width = 800; source.height = 700
const ctx = source.getContext('2d')!
const params = new URLSearchParams(location.search)
evidenceAssets.still = null
ctx.fillStyle = '#19241d'; ctx.fillRect(0, 0, 800, 700)
ctx.fillStyle = '#383124'; ctx.fillRect(0, 410, 800, 290)
evidenceAssets.plate = source.toDataURL()
ctx.clearRect(0, 0, 800, 700)
ctx.fillStyle = '#dcd2b5'; ctx.fillRect(240, 220, 320, 290)
ctx.clearRect(455, 280, 85, 130)
ctx.fillStyle = '#794c2c'; ctx.fillRect(260, 240, 175, 55)
ctx.fillStyle = '#879381'; ctx.fillRect(260, 440, 175, 50)
evidenceAssets.subject = source.toDataURL()
if (params.has('scene')) {
  ctx.globalCompositeOperation = 'destination-over'
  ctx.fillStyle = '#263027'; ctx.fillRect(0, 0, 800, 700)
  ctx.globalCompositeOperation = 'source-over'
  ctx.fillStyle = '#d2b27c'; ctx.font = '22px sans-serif'
  ctx.fillText('OPAQUE SCENE / TEST FIXTURE', 150, 580)
  evidenceAssets.still = source.toDataURL()
}
if (params.has('broken-image')) {
  if (params.has('scene')) evidenceAssets.still = 'data:image/png;base64,broken'
  else evidenceAssets.subject = 'data:image/png;base64,broken'
}
if (params.has('opaque-image')) evidenceAssets.subject = evidenceAssets.plate
createRoot(document.getElementById('root')!).render(<StrictMode><App/><aside style={{position:'fixed',top:0,left:0,right:0,zIndex:200,background:'#201b12',color:'#e7d4ad',textAlign:'center',fontSize:11,pointerEvents:'none'}}>测试专用 · 几何透明图验证 · 非正式证物摄影</aside></StrictMode>)
