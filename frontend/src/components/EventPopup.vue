<script setup lang="ts">
import type { EventProperties } from '../stores/events'

defineProps<{
  feature: { properties: EventProperties }
}>()

const emit = defineEmits<{
  close: []
}>()
</script>

<template>
  <div class="event-popup">
    <button class="close-btn" @click="emit('close')">×</button>
    <h3>{{ feature.properties.title }}</h3>
    <p class="source">{{ feature.properties.source }}</p>
    <p class="date">{{ feature.properties.published_at }}</p>
    <p v-if="feature.properties.location_name" class="location">
      {{ feature.properties.location_name }}
    </p>
  </div>
</template>
