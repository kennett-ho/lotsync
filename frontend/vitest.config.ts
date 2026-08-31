import { defineConfig } from 'vitest/config'

// Deliberately standalone (NOT the app's vite.config.ts): that config
// carries Figma-scaffold HTML/dev-server plugins irrelevant to unit
// tests. The only build-time surface tests need mirrored is the
// __DEALERDOH_RELEASE__ define consumed by src/observability/config.ts.
export default defineConfig({
  define: {
    __DEALERDOH_RELEASE__: JSON.stringify('test'),
  },
  test: {
    environment: 'jsdom',
  },
})
