/**
 * Removes the billing module from this checkout: unlists it in
 * `src/products.ts` and `products.config.js`, and deletes `src/billing/` and
 * its tests. CI runs it on a throwaway checkout to prove the app works without
 * billing; it is also how you would drop billing for real.
 *
 * Fails if the lines it edits have changed, so the CI check can't silently
 * stop removing anything.
 */
import { readFileSync, rmSync, writeFileSync } from 'node:fs'

function edit(path, from, to) {
  const text = readFileSync(path, 'utf8')
  if (!text.includes(from)) {
    console.error(`remove-billing: expected text not found in ${path}:\n  ${from}`)
    process.exit(1)
  }
  writeFileSync(path, text.replace(from, to))
}

edit('src/products.ts', "import billing from '@/billing'\n", '')
edit('src/products.ts', '[billing, ...products]', '[...products]')
edit('products.config.js', "['billing', ...productPackages]", '[...productPackages]')

for (const dir of ['src/billing', 'tests/unit/billing']) {
  rmSync(dir, { recursive: true, force: false })
}

console.log('remove-billing: billing removed from this checkout')
