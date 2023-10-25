<script setup lang="ts">
import { type Validation } from '@vuelidate/core';
import { toMessages } from '@/utils/validation';
import { type ActionDataEntry } from '@/types/action';

const props = withDefaults(
  defineProps<{
    eventType: string;
    eventSubtype: string;
    v$: Validation;
    disableWarning?: boolean;
  }>(),
  {
    disableWarning: false
  }
);

const emit = defineEmits<{
  (e: 'update:event-type', eventType: string): void;
  (e: 'update:event-subtype', eventSubtype: string): void;
}>();

const { eventType, eventSubtype, v$ } = toRefs(props);

const eventTypeModel = computed({
  get() {
    return get(eventType);
  },
  set(newValue: string | null) {
    emit('update:event-type', newValue || '');
  }
});

const eventSubtypeModel = computed({
  get() {
    return get(eventSubtype);
  },
  set(newValue: string | null) {
    emit('update:event-subtype', newValue || '');
  }
});
const {
  getEventTypeData,
  historyEventTypesData,
  historyEventSubTypesData,
  historyEventTypeGlobalMapping
} = useHistoryEventMappings();

const historyTypeCombination = computed(() =>
  get(
    getEventTypeData(
      {
        eventType: get(eventType),
        eventSubtype: get(eventSubtype)
      },
      false
    )
  )
);

const showHistoryEventTypeCombinationWarning = computed(() => {
  const validator = get(v$);
  if (!validator.eventType.$dirty && !validator.eventSubtype.$dirty) {
    return false;
  }

  return !get(historyTypeCombination).identifier;
});

const historyEventSubTypeFilteredData: ComputedRef<ActionDataEntry[]> =
  computed(() => {
    const eventTypeVal = get(eventType);
    const allData = get(historyEventSubTypesData);
    const globalMapping = get(historyEventTypeGlobalMapping);

    if (!eventTypeVal) {
      return allData;
    }

    let globalMappingKeys: string[] = [];

    const globalMappingFound = globalMapping[eventTypeVal];
    if (globalMappingFound) {
      globalMappingKeys = Object.keys(globalMappingFound);
    }

    return allData.filter((data: ActionDataEntry) =>
      globalMappingKeys.includes(data.identifier)
    );
  });

const { t } = useI18n();
</script>

<template>
  <div>
    <div class="grid md:grid-cols-3 gap-4">
      <VAutocomplete
        v-model="eventTypeModel"
        outlined
        required
        :label="t('transactions.events.form.event_type.label')"
        :items="historyEventTypesData"
        item-value="identifier"
        item-text="label"
        data-cy="eventType"
        auto-select-first
        :error-messages="toMessages(v$.eventType)"
        @blur="v$.eventType.$touch()"
      />
      <VAutocomplete
        v-model="eventSubtypeModel"
        outlined
        required
        :label="t('transactions.events.form.event_subtype.label')"
        :items="historyEventSubTypeFilteredData"
        item-value="identifier"
        item-text="label"
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
