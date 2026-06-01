import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useEventsStore } from './events'

const mockFeature = {
  id: 1,
  title: 'Test Event',
  source: 'test-source',
  published_at: '2024-01-15T10:30:00Z',
  location_name: 'Paris',
  country: 'France',
}

describe('events store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('starts with selectedFeature as null', () => {
    const store = useEventsStore()
    expect(store.selectedFeature).toBeNull()
  })

  it('sets selectedFeature on selectFeature', () => {
    const store = useEventsStore()
    store.selectFeature(mockFeature)
    expect(store.selectedFeature).toEqual(mockFeature)
  })

  it('resets selectedFeature to null on clearSelection', () => {
    const store = useEventsStore()
    store.selectFeature(mockFeature)
    store.clearSelection()
    expect(store.selectedFeature).toBeNull()
  })
})
