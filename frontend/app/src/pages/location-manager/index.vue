<script setup lang="ts">
import { msg } from '@/message-key';
import LocationManager from '@/modules/locations/components/LocationManager.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.location_manager'), icon: 'lu-map-pin', section: 2, order: 15, drawer: 'location-manager', addAction: { labelKey: msg.$t('location_manager.actions.add') } },
  },
});
</script>

<template>
  <LocationManager />
</template>
