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
    detailPath: '',
  },
);

const { identifier, detailPath } = toRefs(props);

const { locationData } = useLocations();
const location = locationData(identifier);

const route = computed<{ path: string }>(() => {
  const details = get(detailPath);
  const tradeLocation = get(location);
  let path: string;
  if (details)
    path = details;
  else if (tradeLocation?.detailPath)
    path = tradeLocation.detailPath;
  else if (tradeLocation)
    path = Routes.LOCATIONS.replace(':identifier', tradeLocation.identifier);
  else
    path = '';

  return {
    path,
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
    <LocationIcon
      :item="identifier"
      :icon="icon"
      :size="size"
      class="w-full"
    />
  </NavigatorLink>
</template>
