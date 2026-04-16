<script lang="ts" setup>
import { useLocationStore } from '@/modules/core/common/use-location-store';
import ExchangeDisplay from '@/modules/shell/components/display/ExchangeDisplay.vue';

defineOptions({
  inheritAttrs: false,
});

const model = defineModel<string | undefined>({ required: true });

const { showWithKeyOnly, excludes = [] } = defineProps<{
  dense?: boolean;
  showWithKeyOnly?: boolean;
  excludes?: string[];
}>();

const { allExchanges, exchangesWithKey } = storeToRefs(useLocationStore());

const options = computed<string[]>(() => {
  const exchanges = get(showWithKeyOnly ? exchangesWithKey : allExchanges);
  return exchanges.filter(exchange => !excludes.includes(exchange));
});
</script>

<template>
  <RuiAutoComplete
    v-model="model"
    variant="outlined"
    v-bind="$attrs"
    :options="options"
    :dense="dense"
    :item-height="52"
    auto-select-first
  >
    <template #selection="{ item }">
      <ExchangeDisplay
        :exchange="item"
        :class="`exchange__${item}`"
      />
    </template>
    <template #item="{ item }">
      <ExchangeDisplay
        :exchange="item"
        :class="[`exchange__${item}`, dense && 'py-2']"
      />
    </template>
  </RuiAutoComplete>
</template>
