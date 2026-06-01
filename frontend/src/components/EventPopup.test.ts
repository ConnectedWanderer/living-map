import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import EventPopup from './EventPopup.vue'

const baseFeature = {
  properties: {
    id: 1,
    title: 'Test Event',
    source: 'news-api',
    published_at: '2024-01-15T10:30:00Z',
    location_name: 'Paris',
    country: 'France',
  },
}

describe('EventPopup', () => {
  it('renders the title', () => {
    const wrapper = mount(EventPopup, {
      props: { feature: baseFeature },
    })
    expect(wrapper.text()).toContain('Test Event')
  })

  it('renders the source', () => {
    const wrapper = mount(EventPopup, {
      props: { feature: baseFeature },
    })
    expect(wrapper.text()).toContain('news-api')
  })

  it('renders a formatted date', () => {
    const wrapper = mount(EventPopup, {
      props: { feature: baseFeature },
    })
    expect(wrapper.text()).toContain('2024')
  })

  it('renders the location_name when present', () => {
    const wrapper = mount(EventPopup, {
      props: { feature: baseFeature },
    })
    expect(wrapper.text()).toContain('Paris')
  })

  it('does not render location when location_name is null', () => {
    const feature = {
      properties: { ...baseFeature.properties, location_name: null },
    }
    const wrapper = mount(EventPopup, {
      props: { feature },
    })
    expect(wrapper.text()).not.toContain('Paris')
  })

  it('emits close when close button is clicked', () => {
    const wrapper = mount(EventPopup, {
      props: { feature: baseFeature },
    })
    wrapper.find('button').trigger('click')
    expect(wrapper.emitted('close')).toHaveLength(1)
  })
})
