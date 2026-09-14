// A single scene dissolves as a whole; the older aligned layers remain supported.
// Vite fingerprints these files; no remote URLs or deliberately broken image requests.
const images = import.meta.glob('./media/*.{webp,png,jpg}', { eager: true, query: '?url', import: 'default' }) as Record<string, string>
export const evidenceAssets = {
  plate: images['./media/room.webp'] || null,
  subject: images['./media/evidence.png'] || null,
  still: images['./media/casebook-desk.webp'] || images['./media/casebook-desk.png'] || images['./media/scene.webp'] || null,
}
