import { useEffect, useState } from 'react'

/** One visible-time clock owns the dissolve, compositing, and navigation. */
export function useReducedMotion() {
  const [reduced, setReduced] = useState(() => matchMedia('(prefers-reduced-motion: reduce)').matches)
  useEffect(() => {
    const media = matchMedia('(prefers-reduced-motion: reduce)')
    const change = () => setReduced(media.matches)
    media.addEventListener('change', change)
    return () => media.removeEventListener('change', change)
  }, [])
  return reduced
}

export function visibleClock(tick: (elapsed: number) => boolean) {
  let frame = 0, elapsed = 0, previous = 0, stopped = false
  const animate = (now: number) => {
    if (stopped || document.hidden) return
    if (previous) elapsed += Math.min(now - previous, 80)
    previous = now
    if (tick(elapsed)) frame = requestAnimationFrame(animate)
  }
  const visibility = () => {
    cancelAnimationFrame(frame)
    previous = 0
    if (!document.hidden && !stopped) frame = requestAnimationFrame(animate)
  }
  document.addEventListener('visibilitychange', visibility)
  if (!document.hidden) frame = requestAnimationFrame(animate)
  return () => {
    stopped = true
    cancelAnimationFrame(frame)
    document.removeEventListener('visibilitychange', visibility)
  }
}

export const clamp = (v: number, lo = 0, hi = 1) => Math.min(hi, Math.max(lo, v))
export const smooth = (v: number) => { const t = clamp(v); return t * t * (3 - 2 * t) }
