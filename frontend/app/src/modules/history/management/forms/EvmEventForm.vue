<script setup lang="ts">
import type { EvmHistoryEvent } from '@/modules/history/events/schemas';
import type { StandaloneEventData } from '@/modules/history/management/forms/form-types';
import { HistoryEventEntryType, toSnakeCase } from '@rotki/common';
import { TRADE_LOCATION_EXTERNAL } from '@/modules/core/common/defaults';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import CounterpartyInput from '@/modules/history/events/mapping/CounterpartyInput.vue';
import { useHistoryEventCounterpartyMappings } from '@/modules/history/events/mapping/use-history-event-counterparty-mappings';
import EventDateLocation from '@/modules/history/management/forms/common/EventDateLocation.vue';
import EvmLocation from '@/modules/history/management/forms/common/EvmLocation.vue';
import { EVENT_PRICE_INTENT_KEYS } from '@/modules/history/management/forms/eth-block-event-form';
import {
  emptyEvmEventForm,
  evmEventSchema,
  evmEventStateFromEvent,
  evmEventStateFromGroup,
  toEvmEventEditPayload,
  toEvmEventPayload,
} from '@/modules/history/management/forms/evm-event-form';
import HistoryEventAssetPriceForm from '@/modules/history/management/forms/HistoryEventAssetPriceForm.vue';
import HistoryEventTypeForm from '@/modules/history/management/forms/HistoryEventTypeForm.vue';
import { useEvmTxAutoFill } from '@/modules/history/management/forms/use-evm-tx-lookup';
import { useHistoryEventForm } from '@/modules/history/management/forms/use-history-event-form';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';
import JsonInput from '@/modules/shell/components/inputs/JsonInput.vue';

interface HistoryEventFormProps {
  data: StandaloneEventData<EvmHistoryEvent>;
}

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { data } = defineProps<HistoryEventFormProps>();

const { t } = useI18n({ useScope: 'global' });

// Shared with the transaction lookup below, which reports its failures as field errors too.
const errorMessages = ref<Record<string, string[]>>({});

const { counterparties } = useHistoryEventCounterpartyMappings();
const { txChainsToLocation } = useSupportedChains();

const lastLocation = useLocalStorage('rotki.history_event.location', TRADE_LOCATION_EXTERNAL);

function defaults(): { location: string; nextSequenceId: string } {
  return { location: get(lastLocation) ?? TRADE_LOCATION_EXTERNAL, nextSequenceId: data.nextSequenceId };
}

const { form, save, seed } = useHistoryEventForm({
  errorMessages,
  initial: () => emptyEvmEventForm(defaults()),
  priceIntentKeys: EVENT_PRICE_INTENT_KEYS,
  priceIntents: state => (state.priceIntent ? [state.priceIntent] : []),
  schema: computed(() => evmEventSchema(data.type === 'edit', () => get(counterparties))),
  stateUpdated,
  toEditPayload: toEvmEventEditPayload,
  transform: toEvmEventPayload,
});

const { state } = form;

const isInformationalEvent = computed<boolean>(() => state.eventType === 'informational');

const {
  canRetry: lookupCanRetry,
  loading: lookupLoading,
  needsRelatedAddress: lookupNeedsRelatedAddress,
  reset: resetLookup,
  retry: retryLookup,
} = useEvmTxAutoFill({
  enabled: () => data.type === 'add',
  errorFields: { relatedAddress: 'locationLabel', txHash: 'txRef' },
  errorMessages,
  // Backend expects the canonical chain key (e.g. 'polygon_pos'); the form's
  // `location` carries the human-readable form from `txChainsToLocation`.
  evmChain: () => toSnakeCase(state.location),
  onResolved: (result) => {
    state.timestamp = result.timestamp * 1000;
  },
  relatedAddress: () => state.locationLabel,
  txHash: () => state.txRef,
});

const txRefHint = computed<string>(() => {
  if (get(lookupLoading))
    return t('actions.evm_tx_lookup.loading');
  if (get(lookupNeedsRelatedAddress))
    return t('actions.evm_tx_lookup.needs_related_address');
  return '';
});

function touchEventType(): void {
  form.touch('eventType');
  form.touch('eventSubtype');
}

watchImmediate(() => data, (data) => {
  resetLookup();

  if (data.type === 'edit') {
    seed(evmEventStateFromEvent(data.event, defaults()), [data.event.identifier]);
    return;
  }

  seed(data.type === 'group-add'
    ? evmEventStateFromGroup(data.group, defaults())
    : emptyEvmEventForm(defaults()));
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
      :counterparty="state.counterparty"
      :entry-type="HistoryEventEntryType.EVM_EVENT"
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
      <EventDateLocation
        v-model:timestamp="state.timestamp"
        v-model:location="state.location"
        class="col-span-2"
        :location-disabled="data.type !== 'add'"
        :locations="txChainsToLocation"
        :error-messages="{
          location: form.errors('location'),
          timestamp: form.errors('timestamp'),
        }"
        @blur="form.touch($event)"
      />
    </div>

    <RuiTextField
      v-model="state.txRef"
      variant="outlined"
      color="primary"
      :disabled="data.type !== 'add'"
      data-testid="tx-ref"
      :label="t('common.tx_hash')"
      required
      :hint="txRefHint"
      :error-messages="form.errors('txRef')"
      @blur="form.touch('txRef')"
    >
      <template
        v-if="lookupLoading || lookupCanRetry"
        #append
      >
        <RuiProgress
          v-if="lookupLoading"
          circular
          variant="indeterminate"
          color="primary"
          size="20"
          data-testid="tx-ref-loading"
        />
        <RuiTooltip
          v-else
          :open-delay="400"
        >
          <template #activator>
            <RuiButton
              icon
              variant="text"
              size="sm"
              data-testid="tx-ref-retry"
              @click="retryLookup()"
            >
              <RuiIcon name="lu-refresh-cw" />
            </RuiButton>
          </template>
          {{ t('actions.evm_tx_lookup.retry') }}
        </RuiTooltip>
      </template>
    </RuiTextField>

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
      :no-price-fields="isInformationalEvent"
      @blur="form.touch($event)"
    />

    <RuiDivider class="mb-6 mt-2" />

    <EvmLocation
      v-model:location-label="state.locationLabel"
      v-model:address="state.address"
      :location="state.location"
      :error-messages="{
        locationLabel: form.errors('locationLabel'),
        address: form.errors('address'),
      }"
      @blur="form.touch($event)"
    />

    <div class="grid md:grid-cols-2 gap-4">
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
      <CounterpartyInput
        v-model="state.counterparty"
        :label="t('common.counterparty')"
        data-testid="counterparty"
        :error-messages="form.errors('counterparty')"
        @blur="form.touch('counterparty')"
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

    <RuiDivider class="mb-2 mt-6" />

    <RuiAccordions>
      <RuiAccordion
        data-testid="evm-event-form__advance"
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
            data-testid="groupIdentifier"
            :disabled="state.hasActualGroupIdentifier"
            :label="t('transactions.events.form.group_identifier.label')"
            :error-messages="form.errors('groupIdentifier')"
            @blur="form.touch('groupIdentifier')"
          />

          <JsonInput
            v-model="state.extraData"
            :label="t('transactions.events.form.extra_data.label')"
          />
        </div>
      </RuiAccordion>
    </RuiAccordions>
  </div>
</template>
