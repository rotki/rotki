<script setup lang="ts">
import type { TradeLocationData } from '@/types/history/trade/location';

const props = withDefaults(
  defineProps<{
    modelValue?: string;
    items?: string[];
    excludes?: string[];
    attach?: string;
  }>(),
  {
    value: '',
    items: () => [],
    excludes: () => [],
    attach: undefined,
  },
);

const emit = defineEmits<{
  (e: 'update:model-value', value: string): void;
}>();

const model = useSimpleVModel(props, emit);
const rootAttrs = useAttrs();

const { items, excludes } = toRefs(props);

const { tradeLocations } = useLocations();

const locations = computed<TradeLocationData[]>(() => {
  const itemsVal = get(items);
  const excludesVal = get(excludes);

  return get(tradeLocations).filter((item) => {
    const included
      = itemsVal && itemsVal.length > 0
        ? itemsVal.includes(item.identifier)
        : true;

    const excluded
      = excludesVal && excludesVal.length > 0
        ? excludesVal.includes(item.identifier)
        : false;

    return included && !excluded;
  });
});
</script>

<template>
  <VAutocomplete
    v-bind="rootAttrs"
    v-model="model"
    data-cy="location-input"
    :items="locations"
    item-value="identifier"
    item-title="name"
    auto-select-first
  >
    <template #item="{ item, props }">
      <LocationIcon
        :id="`balance-location__${item.raw.identifier}`"
        v-bind="props"
        horizontal
        :item="item.raw.identifier"
      />
    </template>
    <template #selection="{ item, props }">
      <LocationIcon
        class="pr-2"
        v-bind="props"
        horizontal
        :item="item.raw.identifier"
      />
    </template>
  </VAutocomplete>
</template>
