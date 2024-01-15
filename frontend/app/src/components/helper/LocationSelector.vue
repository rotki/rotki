<script setup lang="ts">
import type { TradeLocationData } from '@/types/history/trade/location';

const props = withDefaults(
  defineProps<{
    value?: string;
    items?: string[];
    excludes?: string[];
    attach?: string;
  }>(),
  { value: '', items: () => [], excludes: () => [], attach: undefined },
);

const emit = defineEmits<{
  (e: 'input', value: string): void;
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
    :attach="attach"
    item-value="identifier"
    item-text="name"
    auto-select-first
    v-on="
      // eslint-disable-next-line vue/no-deprecated-dollar-listeners-api
      $listeners
    "
  >
    <template #item="{ item, attrs, on }">
      <LocationIcon
        :id="`balance-location__${item.identifier}`"
        v-bind="attrs"
        horizontal
        :item="item.identifier"
        v-on="on"
      />
    </template>
    <template #selection="{ item, attrs, on }">
      <LocationIcon
        v-bind="attrs"
        horizontal
        :item="item.identifier"
        v-on="on"
      />
    </template>
  </VAutocomplete>
</template>
