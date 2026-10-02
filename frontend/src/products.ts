/**
 * The product modules installed in this app - the frontend twin of the
 * backend's `src/products.py`. The only runtime file that names a product.
 * Their folder names are also listed in `products.config.js`, which the build
 * (pages, components) and the lint boundary read; keep the two in sync.
 */
import example from '@/example'
import type { ProductModule } from '@/platform/product'

export const products: ProductModule[] = [example]
