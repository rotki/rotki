<script lang="ts" setup generic="TClear = undefined">
import type { ClearedValue, RuiAutoComplete } from '@rotki/ui-library';
import type { ForwardedProps, UnexportedAutoCompleteProps } from '@/modules/core/common/forwarded-props';
import { toClearedValue } from '@/modules/core/common/cleared-value';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { useHistoryEventCounterpartyMappings } from '@/modules/history/events/mapping/use-history-event-counterparty-mappings';
import CounterpartyDisplay from '@/modules/shell/components/display/CounterpartyDisplay.vue';

interface Props {
  excludeExchanges?: boolean;
  /** What clearing writes, `undefined` when not given; `''` keeps a `string` model exact. */
  valueOnClear?: TClear;
  /** The picked counterparty. Not a `defineModel`, since the update is typed apart from the prop. */
  modelValue: string | NoInfer<TClear>;
}

defineOptions({
  inheritAttrs: false,
});

const { excludeExchanges = false, modelValue, valueOnClear } = defineProps<Props & /* @vue-ignore */ ForwardedProps<typeof RuiAutoComplete<string, string>, Props & UnexportedAutoCompleteProps>>();

const emit = defineEmits<{
  'update:model-value': [value: string | ClearedValue<string, TClear, true>];
}>();

const { counterparties } = useHistoryEventCounterpartyMappings();
const { allExchanges } = storeToRefs(useLocationStore());

/** The counterparty the field shows; a clear value that is not one reads as none. */
const selected = computed<string | undefined>(() => (typeof modelValue === 'string' ? modelValue : undefined));

const filteredCounterparties = computed<string[]>(() => {
  if (!excludeExchanges)
    return get(counterparties);

  const exchanges = get(allExchanges);
  return get(counterparties).filter(c => !exchanges.includes(c));
});

/** The field is always clearable, and a cleared field sends the caller's `valueOnClear`. */
function onUpdateModelValue(value: string | undefined): void {
  emit('update:model-value', value ?? toClearedValue<string, TClear, true>(valueOnClear));
}
</script>

<template>
  <RuiAutoComplete
    :model-value="selected"
    clearable
    v-bind="$attrs"
    auto-select-first
    :options="filteredCounterparties"
    @update:model-value="onUpdateModelValue($event)"
  >
    <template #item="{ item }">
      <CounterpartyDisplay :counterparty="item" />
    </template>
    <template #selection="{ item }">
      <CounterpartyDisplay :counterparty="item" />
    </template>
  </RuiAutoComplete>
</template>
