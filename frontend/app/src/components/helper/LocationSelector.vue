<script setup lang="ts">
import type { TradeLocationData } from '@/types/history/trade/location';
import { isEqual } from 'es-toolkit';
import LocationIcon from '@/components/history/LocationIcon.vue';
import { useLocations } from '@/composables/locations';

defineOptions({
  inheritAttrs: false,
});

const model = defineModel<string>({ default: '', required: true });

const props = withDefaults(
  defineProps<{
    items?: string[];
    excludes?: string[];
    dense?: boolean;
  }>(),
  {
    dense: false,
    excludes: () => [],
    items: () => [],
  },
);

const { excludes, items } = toRefs(props);

const { tradeLocations } = useLocations();

const locations = computed<TradeLocationData[]>(() => {
  const itemsVal = get(items);
  const excludesVal = get(excludes);

  return get(tradeLocations).filter((item) => {
    const included = itemsVal && itemsVal.length > 0 ? itemsVal.includes(item.identifier) : true;

    const excluded = excludesVal && excludesVal.length > 0 ? excludesVal.includes(item.identifier) : false;

    return included && !excluded;
  });
});

watch([locations, model], ([locations, value], [prevLocations, prevValue]) => {
  if (isEqual(locations, prevLocations) && value === prevValue)
    return;

  if (!locations.some(item => item.identifier === value))
    set(model, '');
});
</script>

<template>
  <RuiAutoComplete
    v-model="model"
    variant="outlined"
    data-cy="location-input"
    :options="locations"
    key-attr="identifier"
    text-attr="name"
    :item-height="dense ? 36 : 52"
    :dense="dense"
    auto-select-first
    v-bind="$attrs"
  >
    <template #item="{ item }">
      <LocationIcon
        :id="`balance-location__${item.identifier}`"
        class="!justify-start"
        horizontal
        :item="item.identifier"
      />
    </template>
    <template #selection="{ item }">
      <LocationIcon
        class="!justify-start pr-2"
        horizontal
        :item="item.identifier"
      />
    </template>
  </RuiAutoComplete>
</template>
