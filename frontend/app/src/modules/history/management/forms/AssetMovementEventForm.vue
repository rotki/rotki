<script setup lang="ts">
import type { AssetMovementEvent } from '@/modules/history/events/schemas';
import type { GroupEventData } from '@/modules/history/management/forms/form-types';
import { generateUUID } from '@shared/utils';
import { isEqual } from 'es-toolkit';
import ChainSelect from '@/modules/accounts/blockchain/ChainSelect.vue';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import LocationSelector from '@/modules/balances/LocationSelector.vue';
import { TRADE_LOCATION_EXTERNAL } from '@/modules/core/common/defaults';
import {
  ASSET_MOVEMENT_PRICE_INTENT_KEYS,
  assetMovementSchema,
  assetMovementStateFromEvents,
  emptyAssetMovementForm,
  toAssetMovementEditPayload,
  toAssetMovementPayload,
} from '@/modules/history/management/forms/asset-movement-event-form';
import AssetMovementFeeEntry from '@/modules/history/management/forms/common/AssetMovementFeeEntry.vue';
import HistoryEventAssetPriceForm from '@/modules/history/management/forms/HistoryEventAssetPriceForm.vue';
import { useHistoryEventForm } from '@/modules/history/management/forms/use-history-event-form';
import AutoCompleteWithSearchSync from '@/modules/shell/components/inputs/AutoCompleteWithSearchSync.vue';
import DateTimePicker from '@/modules/shell/components/inputs/DateTimePicker.vue';

interface AssetMovementEventFormProps {
  data: GroupEventData<AssetMovementEvent>;
}

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { data } = defineProps<AssetMovementEventFormProps>();

const { t } = useI18n({ useScope: 'global' });

const historyEventTypesData = [{
  identifier: 'receive',
  label: `${t('backend_mappings.events.history_event_subtype.receive')} (${t('backend_mappings.events.history_event_type.deposit')})`,
}, {
  identifier: 'spend',
  label: `${t('backend_mappings.events.history_event_subtype.spend')} (${t('backend_mappings.events.history_event_type.withdrawal')})`,
}];

const lastLocation = useLocalStorage('rotki.history_event.location', TRADE_LOCATION_EXTERNAL);

const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());

const { form, save, seed } = useHistoryEventForm({
  initial: () => emptyAssetMovementForm(get(lastLocation) ?? TRADE_LOCATION_EXTERNAL),
  priceIntentKeys: ASSET_MOVEMENT_PRICE_INTENT_KEYS,
  priceIntents: state => (state.priceIntent ? [state.priceIntent] : []),
  schema: assetMovementSchema(),
  stateUpdated,
  toEditPayload: toAssetMovementEditPayload,
  // A new movement is given an identifier here, a pure transform having no way to make one. An
  // edit keeps whatever it had, blank included, or every save mints it a fresh reference.
  transform: state => toAssetMovementPayload(
    state,
    data.type === 'edit-group' ? state.uniqueId : state.uniqueId || generateUUID(),
  ),
});

const { state } = form;

const locationLabelSuggestions = computed<string[]>(() => {
  const suggestions: string[] = [];

  for (const { location, name } of get(connectedExchanges)) {
    if (location !== state.location || !name) {
      continue;
    }
    suggestions.push(name);
  }
  return suggestions;
});

watchImmediate(() => data, (newData, oldData) => {
  if (isEqual(newData, oldData)) {
    return;
  }

  if (newData.type === 'edit-group') {
    seed(
      assetMovementStateFromEvents(newData.eventsInGroup),
      newData.eventsInGroup.map(event => event.identifier),
    );
    return;
  }

  seed(emptyAssetMovementForm(get(lastLocation) ?? TRADE_LOCATION_EXTERNAL));
});

watch(() => state.location, (location: string) => {
  if (location)
    set(lastLocation, location);
});

watch(() => state.hasFee, (hasFee: boolean) => {
  if (hasFee)
    return;

  state.fee = '';
  state.feeAsset = '';
  state.feeNotes = '';
});

defineExpose({
  errorCount: form.errorCount,
  save,
});
</script>

<template>
  <div>
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
        :disabled="data.type === 'edit-group'"
        data-testid="location"
        :label="t('common.location')"
        required
        :error-messages="form.errors('location')"
        @blur="form.touch('location')"
      />
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
    </div>

    <RuiAutoComplete
      v-model="state.eventSubtype"
      variant="outlined"
      :label="t('transactions.events.form.event_type.label')"
      required
      :options="historyEventTypesData"
      key-attr="identifier"
      text-attr="label"
      data-testid="event-subtype"
      auto-select-first
      :error-messages="form.errors('eventSubtype')"
      @blur="form.touch('eventSubtype')"
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

    <AssetMovementFeeEntry
      v-model:has-fee="state.hasFee"
      v-model:fee="state.fee"
      v-model:fee-asset="state.feeAsset"
      :error-messages="{ fee: form.errors('fee'), feeAsset: form.errors('feeAsset') }"
      @blur="form.touch($event)"
    />

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

    <RuiTextArea
      v-if="state.hasFee"
      v-model="state.feeNotes"
      prepend-icon="lu-sticky-note"
      data-testid="fee-notes"
      variant="outlined"
      color="primary"
      max-rows="5"
      min-rows="3"
      auto-grow
      class="mt-4"
      :label="t('swap_event_form.fee_notes')"
      :hint="t('transactions.events.form.notes.hint')"
      :error-messages="form.errors('feeNotes')"
      @blur="form.touch('feeNotes')"
    />

    <RuiDivider class="mb-2 mt-6" />

    <RuiAccordions>
      <RuiAccordion
        data-testid="asset-movement-event-form-advance"
        header-class="py-4"
        eager
      >
        <template #header>
          {{ t('transactions.events.form.advanced') }}
        </template>
        <div class="py-2">
          <RuiTextField
            v-model="state.groupIdentifier"
            variant="outlined"
            color="primary"
            data-testid="group-identifier"
            :disabled="state.hasActualGroupIdentifier"
            :label="t('transactions.events.form.group_identifier.label')"
            :error-messages="form.errors('groupIdentifier')"
            @blur="form.touch('groupIdentifier')"
          />

          <RuiTextField
            v-model="state.uniqueId"
            variant="outlined"
            data-testid="unique-id"
            color="primary"
            :label="t('transactions.events.form.unique_id.label')"
            :error-messages="form.errors('uniqueId')"
            @blur="form.touch('uniqueId')"
          />

          <RuiTextField
            v-model="state.transactionId"
            variant="outlined"
            color="primary"
            data-testid="tx-ref"
            :label="t('common.tx_hash')"
            :error-messages="form.errors('transactionId')"
            @blur="form.touch('transactionId')"
          />

          <ChainSelect
            v-model="state.blockchain"
            variant="outlined"
            data-testid="blockchain-id"
            color="primary"
            custom-value
            :label="t('common.blockchain')"
            :error-messages="form.errors('blockchain')"
            @blur="form.touch('blockchain')"
          />
        </div>
      </RuiAccordion>
    </RuiAccordions>
  </div>
</template>
