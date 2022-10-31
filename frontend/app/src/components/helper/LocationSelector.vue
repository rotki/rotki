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
    @input="change"
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

<script setup lang="ts">
import { PropType, useListeners } from 'vue';
import LocationIcon from '@/components/history/LocationIcon.vue';
import { TradeLocationData, useTradeLocations } from '@/types/trades';

const props = defineProps({
  value: { required: false, type: String, default: '' },
  items: {
    required: false,
    type: Array as PropType<string[]>,
    default: () => []
  },
  excludes: {
    required: false,
    type: Array as PropType<string[]>,
    default: () => []
  },
  attach: {
    required: false,
    type: String,
    default: undefined
  }
});

const emit = defineEmits<{
  (e: 'change', value: string): void;
}>();

const rootAttrs = useAttrs();
const listeners = useListeners();

const { items, excludes } = toRefs(props);

const change = (_value: string) => emit('change', _value);

const { tradeLocations } = useTradeLocations();

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
