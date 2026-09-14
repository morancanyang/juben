const assets = import.meta.glob<string>('./avatars/*.webp', { eager: true, query: '?url', import: 'default' })

export function npcAvatar(scriptId: string, characterId: string): string | undefined {
  return assets[`./avatars/${scriptId}-${characterId}.webp`]
}
