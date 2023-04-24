<script setup lang="ts">
import { Routes } from '@/router/routes';
import {
  type TradeLocation,
  type TradeLocationData
} from '@/types/history/trade/location';

const props = withDefaults(
  defineProps<{
    identifier: TradeLocation;
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

const { getLocation } = useLocations();

const location: ComputedRef<TradeLocationData> = computed(() =>
  getLocation(identifier)
);

const route = computed<{ path: string }>(() => {
  if (get(detailPath)) {
    return { path: get(detailPath) };
  }

  const path = get(location).detailPath;
  if (path) {
    return { path };
  }

  return {
    path: Routes.LOCATIONS.replace(':identifier', get(location).identifier)
  };
});
</script>

<template>
  <navigator-link :enabled="openDetails" :to="route" component="div">
    <list-item
      v-bind="$attrs"
      class="my-0 text-center"
      :show-details="false"
      :title="location.name"
    >
      <template #icon>
        <location-icon
          class="location-display"
          :item="location"
          :icon="icon"
          :size="size"
        />
      </template>
    </list-item>
  </navigator-link>
</template>

<style scoped lang="scss">
.location-display {
  width: 100%;
}
</style>
