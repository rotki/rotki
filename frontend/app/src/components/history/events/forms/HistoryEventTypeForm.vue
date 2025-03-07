<script setup lang="ts">
import type { ActionDataEntry } from '@/types/action';
import type { Validation } from '@vuelidate/core';
import HistoryEventTypeCombination from '@/components/history/events/HistoryEventTypeCombination.vue';
import { useHistoryEventMappings } from '@/composables/history/events/mapping';
import { toMessages } from '@/utils/validation';

interface HistoryEventTypeFormProps {
  counterparty?: string | null;
  location?: string | null;
  v$: Validation;
  disableWarning?: boolean;
}

const eventType = defineModel<string>('eventType', { required: true });
const eventSubType = defineModel<string | undefined>('eventSubtype', { required: true });

const props = withDefaults(defineProps<HistoryEventTypeFormProps>(), {
  counterparty: null,
  disableWarning: false,
  location: null,
});

const { counterparty, location, v$ } = toRefs(props);

const {
  getEventTypeData,
  historyEventSubTypesData,
  historyEventTypeGlobalMapping,
  historyEventTypesData,
} = useHistoryEventMappings();

const historyTypeCombination = computed(() => get(getEventTypeData({
  counterparty: get(counterparty),
  eventSubtype: get(eventSubType) ?? 'none',
  eventType: get(eventType),
  location: get(location),
}, false)));

const showHistoryEventTypeCombinationWarning = computed(() => {
  const validator = get(v$);
  if (!validator.eventType.$dirty && !validator.eventSubtype.$dirty)
    return false;

  return !get(historyTypeCombination).identifier;
});

const historyEventSubTypeFilteredData = computed<ActionDataEntry[]>(() => {
  const eventTypeVal = get(eventType);
  const allData = get(historyEventSubTypesData);
  const globalMapping = get(historyEventTypeGlobalMapping);

  if (!eventTypeVal)
    return allData;

  let globalMappingKeys: string[] = [];

  const globalMappingFound = globalMapping[eventTypeVal];
  if (globalMappingFound)
    globalMappingKeys = Object.keys(globalMappingFound);

  return allData.filter((data: ActionDataEntry) => globalMappingKeys.includes(data.identifier));
});

const { t } = useI18n();
</script>

<template>
  <div>
    <div class="grid md:grid-cols-3 gap-4">
      <RuiAutoComplete
        v-model="eventType"
        variant="outlined"
        :label="t('transactions.events.form.event_type.label')"
        :options="historyEventTypesData"
        key-attr="identifier"
        text-attr="label"
        data-cy="eventType"
        auto-select-first
        :error-messages="toMessages(v$.eventType)"
        @blur="v$.eventType.$touch()"
      />
      <RuiAutoComplete
        v-model="eventSubType"
        variant="outlined"
        :label="t('transactions.events.form.event_subtype.label')"
        :options="historyEventSubTypeFilteredData"
        key-attr="identifier"
        text-attr="label"
        data-cy="eventSubtype"
        auto-select-first
        :error-messages="toMessages(v$.eventSubtype)"
        @blur="v$.eventSubtype.$touch()"
      />

      <div class="flex flex-col gap-1 -mt-2 md:pl-4 mb-3">
        <div class="text-caption">
          {{ t('transactions.events.form.resulting_combination.label') }}
        </div>
        <HistoryEventTypeCombination
          :type="historyTypeCombination"
          show-label
        />
      </div>
    </div>
    <RuiAlert
      v-if="!disableWarning && showHistoryEventTypeCombinationWarning"
      class="mt-2 mb-6"
      type="warning"
      variant="filled"
      :description="t('transactions.events.form.resulting_combination.unknown')"
    />
  </div>
</template>
