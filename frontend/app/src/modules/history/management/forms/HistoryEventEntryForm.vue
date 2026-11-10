<script setup lang="ts">
import type { EventEntryKind } from '@/modules/history/management/forms/event-entry-form';
import { HistoryEventEntryType } from '@rotki/common';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import CounterpartyInput from '@/modules/history/events/mapping/CounterpartyInput.vue';
import EventDetailsSection from '@/modules/history/management/forms/common/EventDetailsSection.vue';
import EventLocationLabel from '@/modules/history/management/forms/common/EventLocationLabel.vue';
import EvmLocation from '@/modules/history/management/forms/common/EvmLocation.vue';
import TxRefField from '@/modules/history/management/forms/common/TxRefField.vue';
import HistoryEventAssetPriceForm from '@/modules/history/management/forms/HistoryEventAssetPriceForm.vue';
import HistoryEventTypeForm from '@/modules/history/management/forms/HistoryEventTypeForm.vue';
import { type EventEntryFormData, useEventEntryForm } from '@/modules/history/management/forms/use-event-entry-form';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';
import AutoCompleteWithSearchSync from '@/modules/shell/components/inputs/AutoCompleteWithSearchSync.vue';
import DateTimePicker from '@/modules/shell/components/inputs/DateTimePicker.vue';
import JsonInput from '@/modules/shell/components/inputs/JsonInput.vue';

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

/** One form for the plain, bank and chain event entry types; a new event takes its kind from its location. */
const { data, entryType } = defineProps<{
  data: EventEntryFormData;
  /** The entry type picked in the dialog, which a new bank transaction is saved as. */
  entryType?: EventEntryKind;
}>();

const { t } = useI18n({ useScope: 'global' });

const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());

const {
  bitcoinAsset,
  form,
  hasAddress,
  isBitcoin,
  isEvm,
  isPlain,
  lookupCanRetry,
  lookupHint,
  lookupLoading,
  retryLookup,
  save,
} = useEventEntryForm({ data: () => data, entryType: () => entryType, stateUpdated });

const { state } = form;

const isInformationalEvent = computed<boolean>(() => state.eventType === 'informational');

const txRefLabel = computed<string>(() => {
  if (get(isEvm))
    return t('common.tx_hash');
  if (get(isBitcoin))
    return t('transactions.events.form.tx_id.label');
  return t('common.signature');
});

const locationLabelSuggestions = computed<string[]>(() =>
  get(connectedExchanges)
    .map(item => item.name)
    .filter(item => !!item),
);

function touchEventType(): void {
  form.touch('eventType');
  form.touch('eventSubtype');
}

defineExpose({
  errorCount: form.errorCount,
  save,
});
</script>

<template>
  <div>
    <LocationSelector
      v-model="state.location"
      :disabled="data.type !== 'add'"
      data-testid="location"
      :label="t('common.location')"
      required
      :error-messages="form.errors('location')"
      @blur="form.touch('location')"
    />

    <TxRefField
      v-if="!isPlain"
      v-model="state.txRef"
      :disabled="data.type !== 'add'"
      :label="txRefLabel"
      :hint="isEvm ? lookupHint : ''"
      :loading="isEvm && lookupLoading"
      :can-retry="isEvm && lookupCanRetry"
      :error-messages="form.errors('txRef')"
      @blur="form.touch('txRef')"
      @retry="retryLookup()"
    />
    <RuiTextField
      v-else
      v-model="state.groupIdentifier"
      color="primary"
      :disabled="data.type !== 'add' || state.hasActualGroupIdentifier"
      data-testid="group-identifier"
      :label="t('transactions.events.form.group_identifier.label')"
      :required="data.type === 'edit'"
      :error-messages="form.errors('groupIdentifier')"
      @blur="form.touch('groupIdentifier')"
    />

    <DateTimePicker
      v-model="state.timestamp"
      :label="t('common.datetime')"
      required
      max-date="now"
      accuracy="millisecond"
      data-testid="datetime"
      :hint="t('transactions.events.form.datetime.hint')"
      :error-messages="form.errors('timestamp')"
      @blur="form.touch('timestamp')"
    />

    <RuiDivider class="mb-6 mt-2" />

    <HistoryEventTypeForm
      v-model:event-type="state.eventType"
      :event-subtype="state.eventSubtype"
      :counterparty="isPlain ? undefined : state.counterparty"
      :location="isPlain ? state.location : undefined"
      :entry-type="isPlain ? HistoryEventEntryType.HISTORY_EVENT : state.kind"
      :error-messages="{
        eventType: form.errors('eventType'),
        eventSubtype: form.errors('eventSubtype'),
      }"
      show-accounting-rule-link
      :dirty="stateUpdated"
      class="mb-4"
      @touch="touchEventType()"
      @update:event-subtype="state.eventSubtype = $event ?? ''"
    />

    <HistoryEventAssetPriceForm
      v-if="isBitcoin"
      v-model:amount="state.amount"
      v-model:price-intent="state.priceIntent"
      :asset="bitcoinAsset"
      disable-asset
      :location="state.location"
      :error-messages="{ amount: form.errors('amount') }"
      :timestamp="state.timestamp"
      :no-price-fields="isInformationalEvent"
      @blur="form.touch('amount')"
    />
    <HistoryEventAssetPriceForm
      v-else
      v-model:amount="state.amount"
      v-model:price-intent="state.priceIntent"
      :asset="state.asset"
      :location="state.location"
      :error-messages="{
        amount: form.errors('amount'),
        asset: form.errors('asset'),
      }"
      :timestamp="state.timestamp"
      :no-price-fields="!isPlain && isInformationalEvent"
      @blur="form.touch($event)"
      @update:asset="state.asset = $event ?? ''"
    />

    <RuiDivider class="mb-6 mt-2" />

    <EvmLocation
      v-if="hasAddress"
      v-model:location-label="state.locationLabel"
      v-model:address="state.address"
      :location="state.location"
      :error-messages="{
        locationLabel: form.errors('locationLabel'),
        address: form.errors('address'),
      }"
      @blur="form.touch($event)"
    />
    <EventLocationLabel
      v-else-if="!isPlain"
      v-model="state.locationLabel"
      :location="state.location"
      :error-messages="form.errors('locationLabel')"
      @blur="form.touch('locationLabel')"
    />
    <AutoCompleteWithSearchSync
      v-else
      v-model="state.locationLabel"
      :items="locationLabelSuggestions"
      clearable
      data-testid="location-label"
      :label="t('transactions.events.form.location_label.label')"
      :error-messages="form.errors('locationLabel')"
      auto-select-first
      @blur="form.touch('locationLabel')"
    />

    <CounterpartyInput
      v-if="!isPlain"
      :model-value="state.counterparty"
      :label="t('common.counterparty')"
      data-testid="counterparty"
      :error-messages="form.errors('counterparty')"
      @blur="form.touch('counterparty')"
      @update:model-value="state.counterparty = $event ?? ''"
    />

    <RuiDivider class="mb-6 mt-2" />

    <RuiTextArea
      v-model="state.notes"
      data-testid="notes"
      color="primary"
      max-rows="5"
      min-rows="3"
      auto-grow
      :label="t('common.notes')"
      :hint="t('transactions.events.form.notes.hint')"
      :error-messages="form.errors('notes')"
      @blur="form.touch('notes')"
    />

    <RuiDivider class="mb-2 mt-6" />

    <EventDetailsSection
      data-testid="event-entry-form-advance"
      :errors="form.errors"
      :paths="isPlain ? ['sequenceIndex'] : ['sequenceIndex', 'groupIdentifier']"
    >
      <AmountInput
        v-model="state.sequenceIndex"
        integer
        data-testid="sequence-index"
        :label="t('transactions.events.form.sequence_index.label')"
        required
        :error-messages="form.errors('sequenceIndex')"
        @blur="form.touch('sequenceIndex')"
      />

      <template v-if="!isPlain">
        <RuiTextField
          v-model="state.groupIdentifier"
          color="primary"
          data-testid="group-identifier"
          :disabled="state.hasActualGroupIdentifier"
          :label="t('transactions.events.form.group_identifier.label')"
          :error-messages="form.errors('groupIdentifier')"
          @blur="form.touch('groupIdentifier')"
        />

        <JsonInput
          v-model="state.extraData"
          :label="t('transactions.events.form.extra_data.label')"
        />
      </template>
    </EventDetailsSection>
  </div>
</template>
