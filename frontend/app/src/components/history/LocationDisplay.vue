<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';

const props = withDefaults(
  defineProps<{
    identifier: string;
    icon?: boolean;
    size?: string;
    openDetails?: boolean;
    detailPath?: string;
  }>(),
  {
    icon: false,
    size: '24px',
    openDetails: true,
    detailPath: '',
  },
);

const { identifier, detailPath } = toRefs(props);

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
      path: tradeLocation.detailPath,
      hash: '#accounts-section',
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
    />
  </NavigatorLink>
</template>
