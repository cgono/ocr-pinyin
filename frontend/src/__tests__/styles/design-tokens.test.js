import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

function parseTokens() {
  const css = readFileSync(resolve(process.cwd(), 'src/styles/tokens.css'), 'utf8')
  return Object.fromEntries(
    [...css.matchAll(/--([\w-]+):\s*(#[0-9a-fA-F]{6})/g)].map(([, key, value]) => [key, value])
  )
}

function luminance(hex) {
  const rgb = [0, 2, 4]
    .map((index) => parseInt(hex.slice(index + 1, index + 3), 16) / 255)
    .map((channel) => (
      channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4
    ))

  return (0.2126 * rgb[0]) + (0.7152 * rgb[1]) + (0.0722 * rgb[2])
}

function contrastRatio(foreground, background) {
  const fg = luminance(foreground)
  const bg = luminance(background)
  const [lighter, darker] = fg > bg ? [fg, bg] : [bg, fg]
  return (lighter + 0.05) / (darker + 0.05)
}

describe('design tokens', () => {
  it('keep critical text and action colors at WCAG AA contrast', () => {
    const tokens = parseTokens()

    expect(contrastRatio('#ffffff', tokens['color-accent'])).toBeGreaterThanOrEqual(4.5)
    expect(
      contrastRatio(tokens['color-accent-hover'], tokens['color-surface'])
    ).toBeGreaterThanOrEqual(4.5)
    expect(
      contrastRatio(tokens['color-error'], tokens['color-surface-raised'])
    ).toBeGreaterThanOrEqual(4.5)
  })
})
