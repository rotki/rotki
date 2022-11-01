<template>
  <navigator-link :enabled="opensDetails" :to="route" component="div">
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

<script setup lang="ts">
import { ComputedRef, PropType } from 'vue';
import ListItem from '@/components/helper/ListItem.vue';
import NavigatorLink from '@/components/helper/NavigatorLink.vue';
import LocationIcon from '@/components/history/LocationIcon.vue';
import { useLocationInfo } from '@/composables/balances';
import { Routes } from '@/router/routes';
import { TradeLocation } from '@/types/history/trade-location';
import { TradeLocationData } from '@/types/trades';

const props = defineProps({
  identifier: { required: true, type: String as PropType<TradeLocation> },
  icon: { required: false, type: Boolean, default: false },
  size: { required: false, type: String, default: '24px' },
  opensDetails: { required: false, type: Boolean, default: true },
  detailPath: { required: false, type: String, default: '' }
});

const { identifier, detailPath } = toRefs(props);

const { getLocation } = useLocationInfo();

const location: ComputedRef<TradeLocationData> = computed(() =>
  getLocation(get(identifier))
);

const route = computed<{ path: string }>(() => {
  if (get(detailPath)) return { path: get(detailPath) };

  const path = get(location).detailPath;
  if (path) return { path };

  return {
    path: Routes.LOCATIONS.replace(':identifier', get(location).identifier)
  };
});
</script>

<style scoped lang="scss">
.location-display {
  width: 100%;
}
</style>
