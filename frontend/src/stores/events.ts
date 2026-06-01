import { defineStore } from 'pinia'

export interface EventProperties {
  id: number
  title: string
  source: string
  published_at: string
  location_name: string | null
  country: string | null
}

export const useEventsStore = defineStore('events', {
  state: () => ({
    selectedFeature: null as EventProperties | null,
  }),
  actions: {
    selectFeature(feature: EventProperties) {
      this.selectedFeature = feature
    },
    clearSelection() {
      this.selectedFeature = null
    },
  },
})
