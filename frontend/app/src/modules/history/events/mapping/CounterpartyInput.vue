<script lang="ts" setup>
import type { RuiAutoComplete } from '@rotki/ui-library';
import type { ForwardedProps } from '@/modules/core/common/forwarded-props';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { useHistoryEventCounterpartyMappings } from '@/modules/history/events/mapping/use-history-event-counterparty-mappings';
import CounterpartyDisplay from '@/modules/shell/components/display/CounterpartyDisplay.vue';

interface Props {
  excludeExchanges?: boolean;
}

defineOptions({
  inheritAttrs: false,
});

const modelValue = defineModel<string | undefined>({ required: true });

const { excludeExchanges = false } = defineProps<Props & /* @vue-ignore */ ForwardedProps<typeof RuiAutoComplete<string, string>, Props>>();

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
