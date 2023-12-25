<script setup lang="ts">
import { Routes } from '@/router/routes';

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
    detailPath: ''
  }
);

const { identifier, detailPath } = toRefs(props);

const { locationData } = useLocations();
const location = locationData(identifier);

const route = computed<{ path: string }>(() => {
  if (get(detailPath)) {
    return { path: get(detailPath) };
  }

  const tradeLocation = get(location);
  assert(tradeLocation);
  const path = tradeLocation?.detailPath;
  if (path) {
    return { path };
  }

  return {
    path: Routes.LOCATIONS.replace(':identifier', tradeLocation.identifier)
  };
});
</script>

<template>
  <NavigatorLink
    :enabled="openDetails"
    :to="route"
    tag="div"
    :data-location="location?.identifier"
  >
    <LocationIcon :item="identifier" :icon="icon" :size="size" class="w-full" />
  </NavigatorLink>
</template>
