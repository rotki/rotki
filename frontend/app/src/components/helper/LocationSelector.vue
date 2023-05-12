<script setup lang="ts">
import { useListeners } from 'vue';
import { type TradeLocationData } from '@/types/history/trade/location';

const props = withDefaults(
  defineProps<{
    value?: string;
    items?: string[];
    excludes?: string[];
    attach?: string;
  }>(),
  { value: '', items: () => [], excludes: () => [], attach: undefined }
);

const emit = defineEmits<{
  (e: 'change', value: string): void;
}>();

const rootAttrs = useAttrs();
const listeners = useListeners();

const { items, excludes } = toRefs(props);

const change = (_value: string) => emit('change', _value);

const { tradeLocations } = useLocations();

const locations = computed<TradeLocationData[]>(() => {
  const itemsVal = get(items);
  const excludesVal = get(excludes);

  return get(tradeLocations).filter(item => {
    const included =
      itemsVal && itemsVal.length > 0
        ? itemsVal.includes(item.identifier)
        : true;

    const excluded =
      excludesVal && excludesVal.length > 0
        ? excludesVal.includes(item.identifier)
        : false;

    return included && !excluded;
  });
});
</script>

<template>
  <v-autocomplete
    v-bind="rootAttrs"
    data-cy="location-input"
    :value="value"
    :items="locations"
    :attach="attach"
    item-value="identifier"
    item-text="name"
    auto-select-first
    @input="change($event)"
    v-on="listeners"
  >
    <template #item="{ item, attrs, on }">
      <location-icon
        :id="`balance-location__${item.identifier}`"
        v-bind="attrs"
        horizontal
        :item="item"
        no-padding
        v-on="on"
      />
    </template>
    <template #selection="{ item, attrs, on }">
      <location-icon
        v-bind="attrs"
        horizontal
        :item="item"
        no-padding
        v-on="on"
      />
    </template>
  </v-autocomplete>
</template>
