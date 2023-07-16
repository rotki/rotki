<script setup lang="ts">
import { type TradeLocationData } from '@/types/history/trade/location';

const props = defineProps({
  item: {
    required: true,
    type: [Object, String] as PropType<TradeLocationData | string | null>
  },
  horizontal: { required: false, type: Boolean, default: false },
  icon: { required: false, type: Boolean, default: false },
  size: { required: false, type: String, default: '24px' },
  noPadding: { required: false, type: Boolean, default: false }
});

const { item, size } = toRefs(props);

const iconStyle = computed(() => ({
  fontSize: get(size)
}));

const { locationData } = useLocations();

const location: ComputedRef<TradeLocationData | null> = computed(() => {
  const data = get(item);
  if (typeof data === 'string') {
    return get(locationData(data));
  }
  return data;
});
</script>

<template>
  <span
    class="d-flex align-center"
    :class="{
      'flex-row': horizontal,
      'flex-column': !horizontal,
      'py-4': !noPadding
    }"
  >
    <AdaptiveWrapper v-if="!location" tag="span">
      <VSkeletonLoader type="image" :width="size" :height="size" />
    </AdaptiveWrapper>
    <AdaptiveWrapper v-else tag="span">
      <VImg
        v-if="location.image"
        :width="size"
        contain
        position="center"
        :max-height="size"
        :src="location.image"
      />
      <VIcon v-else color="accent" :style="iconStyle">
        {{ location.icon }}
      </VIcon>
    </AdaptiveWrapper>
    <span
      v-if="!icon"
      class="text-capitalize"
      :class="horizontal ? 'ml-3' : null"
    >
      <template v-if="location">
        {{ location.name }}
      </template>
    </span>
  </span>
</template>
