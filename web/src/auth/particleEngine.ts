import { clamp, smooth } from './motion'

type Particle = { x: number; y: number; born: number; life: number; vx: number; vy: number; size: number; spin: number; phase: number; color: string; shard: boolean }
export type DissolveMode = 'subject' | 'scene'

function random(seed: number) { const x = Math.sin(seed * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x) }
function noise(x: number, y: number) {
  const ix = Math.floor(x), iy = Math.floor(y), fx = smooth(x - ix), fy = smooth(y - iy)
  const a = random(ix + iy * 521), b = random(ix + 1 + iy * 521)
  const c = random(ix + (iy + 1) * 521), d = random(ix + 1 + (iy + 1) * 521)
  return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy
}

/** Precompute erosion thresholds and pixel order once; no per-frame allocation per particle. */
export class ParticleEngine {
  private texture = document.createElement('canvas')
  private ctx: CanvasRenderingContext2D
  private data: ImageData
  private order: Uint32Array
  private ends: Uint32Array
  private erased = 0
  private particles: Particle[] = []
  private width: number
  private height: number
  private maxDpr: number
  private lastErosion = -1
  private readonly erosionDuration = 1.95

  constructor(image: HTMLImageElement, mobile: boolean, mode: DissolveMode = 'subject') {
    const ratio = Math.min(1, (mobile ? 560 : 880) / image.naturalWidth)
    this.width = Math.round(image.naturalWidth * ratio)
    this.height = Math.round(image.naturalHeight * ratio)
    if (this.width < 4 || this.height < 4 || this.height > 1800) throw new Error('Unsupported image dimensions')
    this.texture.width = this.width; this.texture.height = this.height
    const ctx = this.texture.getContext('2d', { willReadFrequently: true })
    if (!ctx) throw new Error('Canvas unavailable')
    this.ctx = ctx; ctx.drawImage(image, 0, 0, this.width, this.height)
    this.data = ctx.getImageData(0, 0, this.width, this.height)
    const count = this.width * this.height, rgba = this.data.data
    const distance = new Float32Array(count), thresholds = new Uint8Array(count), bins = new Uint32Array(256)
    let opaque = 0, max = 1
    for (let i = 0; i < count; i++) { distance[i] = rgba[i * 4 + 3] > 16 ? 9999 : 0; if (distance[i]) opaque++ }
    if (opaque < count * .015) throw new Error('Image has no visible content')
    if (mode === 'subject' && opaque > count * .85) throw new Error('A subject alpha cutout is required')
    // Two-pass distance field causes borders/handle/rim to release before the solid interior.
    for (let y = 0; y < this.height; y++) for (let x = 0; x < this.width; x++) {
      const i = x + y * this.width
      distance[i] = Math.min(distance[i], x ? distance[i - 1] + 1 : 0, y ? distance[i - this.width] + 1 : 0)
    }
    for (let y = this.height - 1; y >= 0; y--) for (let x = this.width - 1; x >= 0; x--) {
      const i = x + y * this.width
      distance[i] = Math.min(distance[i], x < this.width - 1 ? distance[i + 1] + 1 : 0, y < this.height - 1 ? distance[i + this.width] + 1 : 0)
      max = Math.max(max, distance[i])
    }
    const fields = new Float32Array(count)
    let earliest = 1, latest = 0
    for (let y = 0; y < this.height; y++) for (let x = 0; x < this.width; x++) {
      const i = x + y * this.width, offset = i * 4
      if (!rgba[offset + 3]) continue
      const luminance = (rgba[offset] + rgba[offset + 1] + rgba[offset + 2]) / 765
      const field = mode === 'scene'
        ? clamp(.08 + .32 * Math.pow(distance[i] / max, .65) + .25 * y / this.height + .42 * noise(x / 29, y / 29) - .12 * luminance)
        : clamp(.08 + .44 * Math.pow(distance[i] / max, .65) + .19 * y / this.height + .3 * noise(x / 23, y / 23) - .09 * luminance)
      fields[i] = field; earliest = Math.min(earliest, field); latest = Math.max(latest, field)
    }
    const step = Math.max(2, Math.ceil(Math.sqrt(opaque / (mobile ? 1700 : 5200))))
    for (let y = 0; y < this.height; y++) for (let x = 0; x < this.width; x++) {
      const i = x + y * this.width, offset = i * 4
      if (!rgba[offset + 3]) continue
      // Normalize the actual cutout's field, so differently shaped evidence all
      // retains interior structure until the final portion of the erosion.
      const threshold = 1 + Math.round(clamp((fields[i] - earliest) / Math.max(.001, latest - earliest)) * 253)
      thresholds[i] = threshold; bins[threshold]++
      if (x % step || y % step || rgba[offset + 3] < 80) continue
      const r = random(i)
      this.particles.push({ x, y, born: .4 + threshold / 255 * this.erosionDuration, life: .65 + r * .85,
        vx: 35 + r * 65, vy: -(22 + random(i + 4) * 68), size: .65 + r * 1.5,
        spin: (random(i + 1) - .5) * 4, phase: random(i + 2) * 6.28,
        color: `rgb(${rgba[offset]},${rgba[offset + 1]},${rgba[offset + 2]})`, shard: r > .965 })
    }
    this.ends = new Uint32Array(256); const cursor = new Uint32Array(256)
    let total = 0
    for (let i = 0; i < 256; i++) { cursor[i] = total; total += bins[i]; this.ends[i] = total }
    this.order = new Uint32Array(total)
    for (let i = 0; i < count; i++) if (rgba[i * 4 + 3]) this.order[cursor[thresholds[i]]++] = i
    this.maxDpr = mobile ? 1.25 : 1.6
  }

  draw(canvas: HTMLCanvasElement, frame: DOMRect, seconds: number) {
    const dpr = Math.min(devicePixelRatio || 1, this.maxDpr)
    const vw = innerWidth, vh = innerHeight
    if (canvas.width !== Math.round(vw * dpr) || canvas.height !== Math.round(vh * dpr)) {
      canvas.width = Math.round(vw * dpr); canvas.height = Math.round(vh * dpr)
    }
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('Canvas lost')
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, vw, vh)
    if (seconds >= .4) {
      const bucket = Math.floor(clamp((seconds - .4) / this.erosionDuration) * 255)
      if (bucket !== this.lastErosion) {
        const end = this.ends[bucket]
        while (this.erased < end) this.data.data[this.order[this.erased++] * 4 + 3] = 0
        this.ctx.putImageData(this.data, 0, 0); this.lastErosion = bucket
      }
    }
    const scale = Math.min(frame.width / this.width, frame.height / this.height)
    const left = frame.left + (frame.width - this.width * scale) / 2
    const top = frame.top + (frame.height - this.height * scale) / 2
    // A restrained rim lift before breakup, returned to normal by the first release.
    if (seconds > 0 && seconds < .4) {
      ctx.shadowColor = `rgba(224,200,151,${Math.sin(seconds / .4 * Math.PI) * .22})`
      ctx.shadowBlur = 5
    }
    ctx.drawImage(this.texture, left, top, this.width * scale, this.height * scale)
    ctx.shadowBlur = 0
    const tail = 1 - smooth((seconds - 2.75) / .45)
    for (const p of this.particles) {
      const age = seconds - p.born
      if (age <= 0 || age >= p.life) continue
      const fade = (1 - smooth(age / p.life)) * tail
      const dx = p.vx * age + Math.sin(age * 2.4 + p.phase) * age * 12
      const dy = p.vy * age + Math.sin(age * 2 + p.phase) * age * 8
      const x = left + p.x * scale + dx * scale, y = top + p.y * scale + dy * scale
      ctx.globalAlpha = fade * .8; ctx.fillStyle = p.color
      if (p.shard) {
        ctx.save(); ctx.translate(x, y); ctx.rotate(p.phase + age * p.spin)
        ctx.fillRect(-p.size, -p.size / 2, p.size * 2.3, p.size * .7); ctx.restore()
      } else {
        // Soft halo provides inexpensive depth without a blur filter per particle.
        ctx.globalAlpha = fade * .1; ctx.beginPath(); ctx.arc(x, y, p.size * 2.2, 0, 6.283); ctx.fill()
        ctx.globalAlpha = fade * .72; ctx.fillRect(x, y, p.size, p.size)
      }
    }
    ctx.globalAlpha = 1
  }

  dispose() { this.particles.length = 0; this.texture.width = 0; this.texture.height = 0 }
}
