const files = import.meta.glob('./scenes/*.webp', { eager: true, query: '?url', import: 'default' }) as Record<string, string>
export function sceneImage(scriptId: string, sceneId: string): string | undefined {
  return files[`./scenes/${scriptId}-${sceneId}.webp`]
}
