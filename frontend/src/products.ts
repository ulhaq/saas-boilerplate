/**
 * The modules installed in this app - the frontend twin of the backend's
 * `src/products.py`: optional platform modules (billing), then the product.
 * The only runtime file that names them. Their folder names are also listed in
 * `products.config.js`, which the build (pages, components) and the lint
 * boundary read; keep the two in sync.
 */
import billing from '@/billing'
import example from '@/example'
import type { Module } from '@/platform/module'

export const products: Module[] = [example]

export const modules: Module[] = [billing, ...products]
