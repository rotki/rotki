<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import { useLocations } from '@/modules/core/common/use-locations';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import NavigatorLink from '@/modules/shell/components/NavigatorLink.vue';

const {
  identifier,
  icon,
  size = '24px',
  openDetails = true,
  detailPath = '',
  horizontal,
} = defineProps<{
  identifier: string;
  icon?: boolean;
  size?: string;
  openDetails?: boolean;
  detailPath?: string;
  horizontal?: boolean;
}>();

const { useLocationData } = useLocations();
const location = useLocationData(() => identifier);

const route = computed<RouteLocationRaw>(() => {
  const details = detailPath;
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
