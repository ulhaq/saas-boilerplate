/**
 * Line icons for the feature list, keyed like `features.list[].key` in the
 * copy. 24x24, stroke-only so they take `currentColor`. Themes decide whether
 * they are shown (`.feature-icon`) or the index number is.
 */
const paths: Record<string, string> = {
  projects: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>',
  teams:
    '<circle cx="9" cy="8" r="3"/><path d="M3 19c0-3 2.7-5 6-5s6 2 6 5"/><path d="M16 5.5a3 3 0 0 1 0 5.5M18 14c1.8.6 3 2.4 3 5"/>',
  rbac: '<rect x="4" y="10" width="16" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/><path d="M12 14v2"/>',
  billing: '<rect x="3" y="6" width="18" height="13" rx="2"/><path d="M3 10h18M7 15h3"/>',
  notifications: '<path d="M6 16V11a6 6 0 1 1 12 0v5l2 2H4Z"/><path d="M10 20a2 2 0 0 0 4 0"/>',
  api: '<path d="m8 8-4 4 4 4M16 8l4 4-4 4M13.5 6l-3 12"/>',
  audit: '<path d="M7 3h8l4 4v14H7Z"/><path d="M15 3v4h4M10 12h6M10 16h6"/>',
  i18n: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.7 3.8 5.7 3.8 9s-1.3 6.3-3.8 9c-2.5-2.7-3.8-5.7-3.8-9S9.5 5.7 12 3Z"/>',
}

export function featureIcon(key: string): string {
  return `<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[key] ?? paths.projects}</svg>`
}
