import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import MapView from './MapView.vue'

const mockMap = {
  on: vi.fn(),
  remove: vi.fn(),
  addControl: vi.fn(),
  setProjection: vi.fn(),
  queryRenderedFeatures: vi.fn().mockReturnValue([]),
}

vi.mock('maplibre-gl', () => {
  const MockNav = vi.fn()
  const MockMap = vi.fn(function () {
    return mockMap
  })
  return {
    default: {
      Map: MockMap,
      NavigationControl: MockNav,
    },
    Map: MockMap,
    NavigationControl: MockNav,
  }
})

describe('MapView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  it('renders a map container div', () => {
    const wrapper = mount(MapView)
    expect(wrapper.find('#map').exists()).toBe(true)
  })

  it('initializes MapLibre with tile URL from api service', async () => {
    mount(MapView)
    const maplibregl = await import('maplibre-gl')
    const MapMock = maplibregl.Map as ReturnType<typeof vi.fn>
    const config = MapMock.mock.calls[0][0]
    const tileUrls = config.style.sources['events-tiles'].tiles
    expect(tileUrls[0]).toContain('/tiles/{z}/{x}/{y}.pbf')
  })
})
