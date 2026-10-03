/** Up-to-two-letter initials for an avatar. Returns '#' for names starting with a digit. */
export function initials(name: string): string {
  const cleaned = name.trim()
  if (/^\d/.test(cleaned)) return '#'
  return cleaned
    .split(/\s+/)
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
}
