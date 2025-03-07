<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import NavigatorLink from '@/components/helper/NavigatorLink.vue';
import LocationIcon from '@/components/history/LocationIcon.vue';
import { useLocations } from '@/composables/locations';

const props = withDefaults(
  defineProps<{
    identifier: string;
    icon?: boolean;
    size?: string;
    openDetails?: boolean;
    detailPath?: string;
    horizontal?: boolean;
  }>(),
  {
    detailPath: '',
    horizontal: false,
    icon: false,
    openDetails: true,
    size: '24px',
  },
);

const { detailPath, identifier } = toRefs(props);

const { locationData } = useLocations();
const location = locationData(identifier);

const route = computed<RouteLocationRaw>(() => {
  const details = get(detailPath);
  const tradeLocation = get(location);
  if (details) {
    return { path: details };
  }
  else if (tradeLocation?.detailPath) {
    return {
      hash: '#accounts-section',
      path: tradeLocation.detailPath,
    };
  }
  else if (tradeLocation) {
    return {
      name: '/locations/[identifier]',
      params: {
        identifier: tradeLocation.identifier,
      },
    };
  }
  else {
    return { path: '' };
  }
});
</script>

<template>
  <NavigatorLink
    :enabled="openDetails"
    :to="route"
    tag="div"
    :data-location="location?.identifier"
  >
    <LocationIcon
      :item="identifier"
      :icon="icon"
      :size="size"
      class="w-full"
      :horizontal="horizontal"
    />
  </NavigatorLink>
</template>
