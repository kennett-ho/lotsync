/**
 * Release C (v1.1) regression guard: the pre-auth surfaces -- Login,
 * ResetPassword (invite/recovery landing), and the ErrorBoundary
 * fallback -- must show the DEV synthetic-data warning ONLY in builds
 * with VITE_ENVIRONMENT=development (the DEV Vercel project), and
 * neutral DealerDOH copy everywhere else. Production once shipped the
 * hardcoded DEV banner over real dealership data; these tests pin the
 * fix.
 *
 * The components read VITE_ENVIRONMENT at module load (the App.tsx
 * DevBanner idiom), so each case stubs the env FIRST and then imports
 * the module fresh -- vi.resetModules() in afterEach makes the next
 * import re-evaluate against the next stub.
 */

import { afterEach, describe, expect, test, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import React from 'react'

const FORBIDDEN_IN_PRODUCTION = [
  /DealerDOH DEV/,
  /Development Environment/,
  /Synthetic\/Test Data Only/,
  /Sign in to the development dealership/,
]

// Residual dev-flavored copy removed by owner decision after the
// Release C promotion -- forbidden in EVERY environment, DEV included
// (unlike the banner, these had no dev-side purpose).
const FORBIDDEN_EVERYWHERE = [
  /Development accounts are provisioned/,
  /qa\.dealerdoh\.example/,
]

function expectNoResidualCopy() {
  for (const pattern of FORBIDDEN_EVERYWHERE) {
    expect(screen.queryByText(pattern)).toBeNull()
    expect(screen.queryByPlaceholderText(pattern)).toBeNull()
  }
}

afterEach(() => {
  cleanup()
  vi.unstubAllEnvs()
  vi.resetModules()
  vi.restoreAllMocks()
})

async function renderFresh(
  modulePath: string,
  environment: string | undefined,
  wrap?: (el: React.ReactElement) => React.ReactElement,
) {
  if (environment !== undefined) vi.stubEnv('VITE_ENVIRONMENT', environment)
  const { default: Component } = await import(modulePath)
  const element = React.createElement(Component)
  render(wrap ? wrap(element) : element)
}

function expectNoForbiddenCopy() {
  for (const pattern of FORBIDDEN_IN_PRODUCTION) {
    expect(screen.queryByText(pattern)).toBeNull()
  }
}

describe('Login', () => {
  test('production renders neutral copy and no DEV messaging', async () => {
    await renderFresh('./auth/Login', 'production')
    expectNoForbiddenCopy()
    expectNoResidualCopy()
    expect(screen.getByText('DealerDOH')).not.toBeNull()
    expect(screen.getByText('Sign in to your dealership workspace.')).not.toBeNull()
    expect(screen.getByPlaceholderText('you@dealership.com')).not.toBeNull()
  })

  test('unset environment (local build) also renders neutral copy', async () => {
    await renderFresh('./auth/Login', undefined)
    expectNoForbiddenCopy()
    expectNoResidualCopy()
    expect(screen.getByText('Sign in to your dealership workspace.')).not.toBeNull()
  })

  test('development keeps the DEV banner and development copy', async () => {
    await renderFresh('./auth/Login', 'development')
    expect(screen.getByText(/Synthetic\/Test Data Only/)).not.toBeNull()
    expect(screen.getByText('Sign in to the development dealership')).not.toBeNull()
    expect(screen.queryByText('Sign in to your dealership workspace.')).toBeNull()
    expectNoResidualCopy()
  })
})

describe('ResetPassword', () => {
  test('production renders neutral copy and no DEV messaging', async () => {
    await renderFresh('./auth/ResetPassword', 'production')
    expectNoForbiddenCopy()
    expect(screen.getByText('DealerDOH')).not.toBeNull()
    expect(screen.getByText('Set your password')).not.toBeNull()
  })

  test('development keeps the DEV banner', async () => {
    await renderFresh('./auth/ResetPassword', 'development')
    expect(screen.getByText(/Synthetic\/Test Data Only/)).not.toBeNull()
  })
})

describe('ErrorBoundary fallback', () => {
  // The boundary catches a render throw; React logs it to
  // console.error -- silenced so the suite output stays readable.
  function Boom(): never {
    throw new Error('deliberate test render failure')
  }

  async function renderCrashed(environment: string) {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    await renderFresh('./observability/ErrorBoundary', environment, el =>
      React.cloneElement(el, {}, React.createElement(Boom)),
    )
  }

  test('production fallback has neutral copy and no DEV messaging', async () => {
    await renderCrashed('production')
    expectNoForbiddenCopy()
    expect(screen.getByText('DealerDOH hit an unexpected problem')).not.toBeNull()
  })

  // The dev-side branch (banner present under VITE_ENVIRONMENT=
  // development) is NOT asserted here: ErrorBoundary's pre-existing
  // gate reads the env through observability/config.ts's cast-style
  // access, which Vitest's transform cannot see (only direct
  // import.meta.env accesses honor vi.stubEnv). The production case
  // above still guards the release requirement -- a reintroduced
  // unconditional banner fails it -- and the dev banner is exercised
  // daily on the DEV deployment itself.
})
