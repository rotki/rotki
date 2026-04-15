<script setup lang="ts">
import type { TradeLocationData } from '@/modules/history/trade/location';
import { isEqual } from 'es-toolkit';
import LocationIcon from '@/components/history/LocationIcon.vue';
import { useLocations } from '@/composables/locations';

defineOptions({
  inheritAttrs: false,
});

const model = defineModel<string>({ default: '', required: true });

const { dense, excludes = [], items = [] } = defineProps<{
  items?: string[];
  excludes?: string[];
  dense?: boolean;
}>();

const { tradeLocations } = useLocations();

const locations = computed<TradeLocationData[]>(() => get(tradeLocations).filter((item) => {
  const included = items && items.length > 0 ? items.includes(item.identifier) : true;
  const excluded = excludes && excludes.length > 0 ? excludes.includes(item.identifier) : false;

  return included && !excluded;
}));

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
