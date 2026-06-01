<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { TILE_URL } from '../services/api'
import EventPopup from './EventPopup.vue'
import { useEventsStore, type EventProperties } from '../stores/events'

const store = useEventsStore()

let map: maplibregl.Map | null = null
onMounted(() => {
  map = new maplibregl.Map({
    container: 'map',
    style: {
      version: 8,
      sources: {
        'osm-raster': {
          type: 'raster',
          tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
          tileSize: 256,
          attribution: '© OpenStreetMap contributors',
        },
        'events-tiles': {
          type: 'vector',
          tiles: [TILE_URL],
        },
      },
      layers: [
        { id: 'osm-raster', type: 'raster', source: 'osm-raster', minzoom: 0 },
        {
          id: 'events-circle',
          type: 'circle',
          source: 'events-tiles',
          'source-layer': 'events',
          paint: {
            'circle-color': '#ff6b6b',
            'circle-radius': [
              'interpolate',
              ['exponential', 0.5],
              ['zoom'],
              0, 2,
              10, 6,
              16, 12,
            ],
            'circle-opacity': 0.8,
            'circle-stroke-color': '#ffffff',
            'circle-stroke-width': 1.5,
          },
        },
      ],
    },
    zoom: 2,
    center: [0, 20],
  })

  map.on('load', () => {
    map!.setProjection({ type: 'globe' } as maplibregl.ProjectionSpecification)
  })

  map.on('error', (e) => {
    console.error('Map error:', e.error?.message ?? e)
  })

  map.addControl(new maplibregl.NavigationControl())

  map.on('click', 'events-circle', (e) => {
    if (e.features && e.features[0]) {
      const feature = e.features[0] as unknown as { properties: EventProperties }
      store.selectFeature(feature.properties as EventProperties)
    }
  })

  map.on('click', (e) => {
    const features = map!.queryRenderedFeatures(e.point)
    if (!features.some((f) => f.layer.id === 'events-circle')) {
      store.clearSelection()
    }
  })
})

onUnmounted(() => {
  map?.remove()
})
</script>

<template>
  <div id="map" class="map-container">
    <EventPopup
      v-if="store.selectedFeature"
      :feature="{ properties: store.selectedFeature }"
      @close="store.clearSelection()"
    />
  </div>
</template>

<style scoped>
.map-container {
  width: 100%;
  height: 100%;
}
</style>
