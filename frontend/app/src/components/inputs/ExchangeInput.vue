<script lang="ts" setup>
import ExchangeDisplay from '@/components/display/ExchangeDisplay.vue';
import { useLocationStore } from '@/store/locations';

defineOptions({
  inheritAttrs: false,
});

const model = defineModel<string | undefined>({ required: true });

const props = withDefaults(defineProps<{
  dense?: boolean;
  showWithKeyOnly?: boolean;
  excludes?: string[];
}>(), {
  excludes: () => [],
  showWithKeyOnly: false,
});

const { allExchanges, exchangesWithKey } = storeToRefs(useLocationStore());

const options = computed<string[]>(() => {
  const exchanges = get(props.showWithKeyOnly ? exchangesWithKey : allExchanges);
  return exchanges.filter(exchange => !props.excludes.includes(exchange));
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
