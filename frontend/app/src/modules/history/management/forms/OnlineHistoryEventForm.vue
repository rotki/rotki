<script setup lang="ts">
import type { NewOnlineHistoryEventPayload, OnlineHistoryEvent } from '@/modules/history/events/schemas';
import type { StandaloneEventData } from '@/modules/history/management/forms/form-types';
import { HistoryEventEntryType } from '@rotki/common';
import { generateUUID } from '@shared/utils';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import { TRADE_LOCATION_EXTERNAL } from '@/modules/core/common/defaults';
import { EVENT_PRICE_INTENT_KEYS } from '@/modules/history/management/forms/eth-block-event-form';
import HistoryEventAssetPriceForm from '@/modules/history/management/forms/HistoryEventAssetPriceForm.vue';
import HistoryEventTypeForm from '@/modules/history/management/forms/HistoryEventTypeForm.vue';
import {
  emptyOnlineHistoryForm,
  onlineHistorySchema,
  onlineHistoryStateFromEvent,
  onlineHistoryStateFromGroup,
  toOnlineHistoryEditPayload,
  toOnlineHistoryPayload,
} from '@/modules/history/management/forms/online-history-event-form';
import { useHistoryEventForm } from '@/modules/history/management/forms/use-history-event-form';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';
import AutoCompleteWithSearchSync from '@/modules/shell/components/inputs/AutoCompleteWithSearchSync.vue';
import DateTimePicker from '@/modules/shell/components/inputs/DateTimePicker.vue';

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { data } = defineProps<{ data: StandaloneEventData<OnlineHistoryEvent> }>();

const { t } = useI18n({ useScope: 'global' });

const lastLocation = useLocalStorage('rotki.history_event.location', TRADE_LOCATION_EXTERNAL);

const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());

function defaults(): { location: string; nextSequenceId: string } {
  return { location: get(lastLocation) ?? TRADE_LOCATION_EXTERNAL, nextSequenceId: data.nextSequenceId };
}

const { form, save, seed } = useHistoryEventForm({
  initial: () => emptyOnlineHistoryForm(defaults()),
  priceIntentKeys: EVENT_PRICE_INTENT_KEYS,
  priceIntents: state => (state.priceIntent ? [state.priceIntent] : []),
  schema: computed(() => onlineHistorySchema(data.type === 'edit')),
  stateUpdated,
  toEditPayload: toOnlineHistoryEditPayload,
  // A new event needs a group of its own, which a pure transform cannot produce.
  transform: (state): NewOnlineHistoryEventPayload =>
    toOnlineHistoryPayload(state, state.groupIdentifier || generateUUID()),
});

const { state } = form;

const locationLabelSuggestions = computed<string[]>(() =>
  get(connectedExchanges)
    .map(item => item.name)
    .filter(item => !!item),
);

function touchEventType(): void {
  form.touch('eventType');
  form.touch('eventSubtype');
}

watchImmediate(() => data, (data) => {
  if (data.type === 'edit') {
    seed(onlineHistoryStateFromEvent(data.event, defaults()), [data.event.identifier]);
    return;
  }

  seed(data.type === 'group-add'
    ? onlineHistoryStateFromGroup(data.group, defaults())
    : emptyOnlineHistoryForm(defaults()));
});

watch(() => state.location, (location: string) => {
  if (location)
    set(lastLocation, location);
});

defineExpose({
  errorCount: form.errorCount,
  save,
});
</script>

<template>
  <div>
    <HistoryEventTypeForm
      v-model:event-type="state.eventType"
      v-model:event-subtype="state.eventSubtype"
      :location="state.location"
      :entry-type="HistoryEventEntryType.HISTORY_EVENT"
      :error-messages="{
        eventType: form.errors('eventType'),
        eventSubtype: form.errors('eventSubtype'),
      }"
      show-accounting-rule-link
      :dirty="stateUpdated"
      class="mb-4"
      @touch="touchEventType()"
    />

    <div class="grid md:grid-cols-2 gap-4 mb-4">
      <DateTimePicker
        v-model="state.timestamp"
        :label="t('common.datetime')"
        required
        persistent-hint
        max-date="now"
        variant="outlined"
        accuracy="millisecond"
        data-testid="datetime"
        :hint="t('transactions.events.form.datetime.hint')"
        :error-messages="form.errors('timestamp')"
        @blur="form.touch('timestamp')"
      />
      <LocationSelector
        v-model="state.location"
        :disabled="data.type !== 'add'"
        data-testid="location"
        :label="t('common.location')"
        required
        :error-messages="form.errors('location')"
        @blur="form.touch('location')"
      />
    </div>

    <RuiTextField
      v-model="state.groupIdentifier"
      variant="outlined"
      color="primary"
      :disabled="data.type !== 'add' || state.hasActualGroupIdentifier"
      data-testid="group-identifier"
      :label="t('transactions.events.form.group_identifier.label')"
      :required="data.type === 'edit'"
      :error-messages="form.errors('groupIdentifier')"
      @blur="form.touch('groupIdentifier')"
    />

    <RuiDivider class="mb-6 mt-2" />

    <HistoryEventAssetPriceForm
      v-model:asset="state.asset"
      v-model:amount="state.amount"
      v-model:price-intent="state.priceIntent"
      :location="state.location"
      :error-messages="{
        amount: form.errors('amount'),
        asset: form.errors('asset'),
      }"
      :timestamp="state.timestamp"
      @blur="form.touch($event)"
    />

    <RuiDivider class="mb-6 mt-2" />

    <div class="grid md:grid-cols-2 gap-4">
      <AutoCompleteWithSearchSync
        v-model="state.locationLabel"
        :items="locationLabelSuggestions"
        clearable
        data-testid="location-label"
        :label="t('transactions.events.form.location_label.label')"
        :error-messages="form.errors('locationLabel')"
        auto-select-first
        @blur="form.touch('locationLabel')"
      />
      <AmountInput
        v-model="state.sequenceIndex"
        variant="outlined"
        integer
        data-testid="sequence-index"
        :label="t('transactions.events.form.sequence_index.label')"
        required
        :error-messages="form.errors('sequenceIndex')"
        @blur="form.touch('sequenceIndex')"
      />
    </div>

    <RuiDivider class="mb-6 mt-2" />

    <RuiTextArea
      v-model="state.notes"
      prepend-icon="lu-sticky-note"
      data-testid="notes"
      variant="outlined"
      color="primary"
      max-rows="5"
      min-rows="3"
      auto-grow
      :label="t('common.notes')"
      :hint="t('transactions.events.form.notes.hint')"
      :error-messages="form.errors('notes')"
      @blur="form.touch('notes')"
    />
  </div>
</template>
