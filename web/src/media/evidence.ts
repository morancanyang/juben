// Vite imports every image into the production build with a content-hashed URL.
const images = import.meta.glob<string>('./evidence/*.webp', {
  eager: true,
  query: '?url',
  import: 'default',
})

const tutorial: Record<string, { title: string; description: string }> = {
  log: { title: '开柜日志', description: '19:12，维护卡 C-04 打开展柜。' },
  glove: { title: '银粉手套', description: '手套掌心留有银色粉末。' },
  note: { title: '收藏商收购便笺', description: '便笺约定当晚收购一枚相同编号的银徽章。' },
}

export function evidenceImage(scriptId: string, evidence: { id: string; title: string; description: string }): string | undefined {
  const direct = images[`./evidence/${scriptId}-${evidence.id}.webp`]
  if (direct) return direct
  // Frozen teaching drafts have owner-prefixed IDs. Reuse their art only while
  // the evidence content still matches; edited user content must not get false clues.
  const original = tutorial[evidence.id]
  if (original?.title === evidence.title && original.description === evidence.description) {
    return images[`./evidence/museum-example-${evidence.id}.webp`]
  }
}
