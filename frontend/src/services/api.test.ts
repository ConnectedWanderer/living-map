import { describe, it, expect } from 'vitest'
import { TILE_URL } from './api'

describe('api service', () => {
  it('exports a TILE_URL with the tile pattern', () => {
    expect(TILE_URL).toContain('/tiles/{z}/{x}/{y}.pbf')
  })
})
