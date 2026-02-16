<script lang="ts" setup>
import CounterpartyDisplay from '@/components/history/CounterpartyDisplay.vue';
import { useHistoryEventCounterpartyMappings } from '@/composables/history/events/mapping/counterparty';
import { useLocationStore } from '@/store/locations';

defineOptions({
  inheritAttrs: false,
});

const modelValue = defineModel<string | undefined>({ required: true });

const { excludeExchanges = false } = defineProps<{
  excludeExchanges?: boolean;
}>();

const { counterparties } = useHistoryEventCounterpartyMappings();
const { allExchanges } = storeToRefs(useLocationStore());

const filteredCounterparties = computed<string[]>(() => {
  if (!excludeExchanges)
    return get(counterparties);

  const exchanges = get(allExchanges);
  return get(counterparties).filter(c => !exchanges.includes(c));
});
</script>

<template>
  <RuiAutoComplete
    v-model="modelValue"
    variant="outlined"
    clearable
    v-bind="$attrs"
    auto-select-first
    :options="filteredCounterparties"
  >
    <template #item="{ item }">
      <CounterpartyDisplay :counterparty="item" />
    </template>
    <template #selection="{ item }">
      <CounterpartyDisplay :counterparty="item" />
    </template>
  </RuiAutoComplete>
</template>
