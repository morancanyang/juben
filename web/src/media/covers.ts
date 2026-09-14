const files = import.meta.glob('./covers/*.{webp,png,jpg}', { eager: true, query: '?url', import: 'default' }) as Record<string, string>
export const coverImages: Record<string, string | undefined> = {
  train: files['./covers/train.webp'],
  manor: files['./covers/manor.webp'],
  station: files['./covers/station.webp'],
}
