import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import App from './App.vue'

vi.mock('maplibre-gl', () => {
  const MockNav = vi.fn()
  const MockMap = vi.fn(function () {
    return { on: vi.fn(), remove: vi.fn(), addControl: vi.fn() }
  })
  return {
    default: { Map: MockMap, NavigationControl: MockNav },
    Map: MockMap,
    NavigationControl: MockNav,
  }
})

describe('App', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders the map view', () => {
    const wrapper = mount(App)
    expect(wrapper.find('#map').exists()).toBe(true)
  })
})
