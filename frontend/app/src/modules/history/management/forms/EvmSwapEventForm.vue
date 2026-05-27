<script lang="ts" setup>
import type { AddEvmSwapEventPayload, EvmHistoryEvent, EvmSwapEvent } from '@/modules/history/events/schemas';
import type { EvmSwapFormData } from '@/modules/history/management/forms/evm-swap-event-form';
import type { GroupEventData, StandaloneEventData } from '@/modules/history/management/forms/form-types';
import { assert, HistoryEventEntryType, toSnakeCase } from '@rotki/common';
import dayjs from 'dayjs';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useRefPropVModel } from '@/modules/core/common/validation/model';
import CounterpartyInput from '@/modules/history/events/mapping/CounterpartyInput.vue';
import EventDateLocation from '@/modules/history/management/forms/common/EventDateLocation.vue';
import SwapSubEventList from '@/modules/history/management/forms/swap/SwapSubEventList.vue';
import { toMessages, useEventFormBase } from '@/modules/history/management/forms/use-event-form-base';
import { useEvmTxAutoFill } from '@/modules/history/management/forms/use-evm-tx-lookup';
import { useSwapEventForm } from '@/modules/history/management/forms/use-swap-event-form';
import { toSubEvent } from '@/modules/history/management/forms/utils';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { data } = defineProps<{ data: StandaloneEventData<EvmHistoryEvent> | GroupEventData<EvmSwapEvent> }>();

const { txChainsToLocation } = useSupportedChains();
const { emptySubEvent, handleValidationErrors, submitAllPrices, addHistoryEvent, editHistoryEvent } = useSwapEventForm();

function emptyEvent(): EvmSwapFormData {
  return {
    address: '',
    counterparty: '',
    entryType: HistoryEventEntryType.EVM_SWAP_EVENT,
    fee: [],
    location: '',
    receive: [emptySubEvent()],
    sequenceIndex: '0',
    spend: [emptySubEvent()],
    timestamp: dayjs().valueOf(),
    txRef: '',
  };
}

const states = ref<EvmSwapFormData>(emptyEvent());
const hasFee = ref<boolean>(false);
const identifiers = ref<number[]>([]);
const errorMessages = ref<Record<string, string[]>>({});

const spendListRef = useTemplateRef<InstanceType<typeof SwapSubEventList>>('spendListRef');
const receiveListRef = useTemplateRef<InstanceType<typeof SwapSubEventList>>('receiveListRef');
const feeListRef = useTemplateRef<InstanceType<typeof SwapSubEventList>>('feeListRef');

const timestamp = useRefPropVModel(states, 'timestamp');

const { t } = useI18n({ useScope: 'global' });

const { v$, captureEditModeState, shouldSkipSave } = useEventFormBase({
  rules: commonRules => computed(() => ({
    address: commonRules.createValidEthAddressRule(),
    counterparty: commonRules.createExternalValidationRule(),
    fee: get(hasFee) ? commonRules.createRequiredAtLeastOne() : {},
    location: commonRules.createRequiredLocationRule(),
    receive: commonRules.createRequiredAtLeastOne(),
    sequenceIndex: commonRules.createRequiredSequenceIndexRule(),
    spend: commonRules.createRequiredAtLeastOne(),
    timestamp: commonRules.createExternalValidationRule(),
    txRef: commonRules.createValidTxHashRule(),
  })),
  states,
  errorMessages,
  stateUpdated,
});

const {
  canRetry: lookupCanRetry,
  loading: lookupLoading,
  needsRelatedAddress: lookupNeedsRelatedAddress,
  reset: resetLookup,
  retry: retryLookup,
} = useEvmTxAutoFill({
  enabled: () => data.type === 'add',
  // The swap form has no dedicated tracked-address field; route validation
  // errors to the tx-hash field with a hint pointing the user at the spend list.
  errorFields: { relatedAddress: 'txRef', txHash: 'txRef' },
  errorMessages,
  evmChain: () => toSnakeCase(get(states).location),
  onResolved: (result) => {
    set(states, { ...get(states), timestamp: result.timestamp * 1000 });
  },
  // Use the first spend sub-event's locationLabel as the user's tracked address.
  relatedAddress: () => get(states).spend[0]?.locationLabel ?? '',
  txHash: () => get(states).txRef,
});

const txRefHint = computed<string>(() => {
  if (get(lookupLoading))
    return t('actions.evm_tx_lookup.loading');
  if (get(lookupNeedsRelatedAddress))
    return t('actions.evm_tx_lookup.needs_related_address_swap');
  return '';
});

async function save(): Promise<boolean> {
  if (!(await get(v$).$validate())) {
    return false;
  }

  const isEditMode = get(identifiers).length > 0;

  // Submit prices from all nested HistoryEventAssetPriceForm components
  const pricesSubmitted = await submitAllPrices({ spendListRef, receiveListRef, feeListRef });
  if (!pricesSubmitted) {
    return false;
  }

  if (shouldSkipSave(isEditMode, get(states))) {
    return true;
  }

  const payload: AddEvmSwapEventPayload = { ...get(states) };

  if (!get(hasFee)) {
    delete payload.fee;
  }

  if (payload.address === '') {
    payload.address = undefined;
  }

  const result = isEditMode
    ? await editHistoryEvent({
        ...payload,
        ...{
          identifiers: get(identifiers),
        },
      })
    : await addHistoryEvent(payload);

  if (result.success) {
    set(states, emptyEvent());
    set(identifiers, []);
    set(hasFee, false);
  }
  else {
    const message = result.message;
    if (message) {
      handleValidationErrors(message);
      set(errorMessages, typeof message === 'string' ? {} : message);
    }
  }

  return result.success;
}

watchImmediate(() => data, (data) => {
  resetLookup();
  if (data.type === 'group-add') {
    const group = data.group;

    set(states, {
      ...get(states),
      location: group.location ?? '',
      sequenceIndex: data.nextSequenceId.toString(),
      timestamp: group.timestamp,
      txRef: group.txRef,
    });
  }
  else if (data.type === 'edit-group') {
    const spend = data.eventsInGroup.filter(item => item.eventSubtype === 'spend');
    const receive = data.eventsInGroup.filter(item => item.eventSubtype === 'receive');
    const fee = data.eventsInGroup.filter(item => item.eventSubtype === 'fee');

    assert(spend.length > 0);
    assert(receive.length > 0);

    set(hasFee, fee.length > 0);
    set(identifiers, data.eventsInGroup.map(item => item.identifier));

    const firstSpend = spend[0];
    set(states, {
      address: firstSpend.address ?? '',
      counterparty: firstSpend.counterparty ?? '',
      entryType: HistoryEventEntryType.EVM_SWAP_EVENT,
      fee: fee.map(event => toSubEvent(event)),
      location: firstSpend.location,
      receive: receive.map(event => toSubEvent(event)),
      sequenceIndex: firstSpend.sequenceIndex.toString(),
      spend: spend.map(event => toSubEvent(event)),
      timestamp: firstSpend.timestamp,
      txRef: firstSpend.txRef,
    });

    captureEditModeState(get(states));
  }
});

watch(hasFee, (hasFee) => {
  set(states, { ...get(states), fee: hasFee ? [emptySubEvent()] : [] });
});

defineExpose({
  save,
  v$,
});
</script>

<template>
  <div>
    <EventDateLocation
      v-model:timestamp="timestamp"
      v-model:location="states.location"
      :location-disabled="data.type !== 'add'"
      :locations="txChainsToLocation"
      :error-messages="{
        location: toMessages(v$.location),
        timestamp: toMessages(v$.timestamp),
      }"
      @blur="v$[$event].$touch()"
    />

    <RuiDivider class="mb-6 mt-2" />

    <RuiTextField
      v-model="states.txRef"
      variant="outlined"
      color="primary"
      :disabled="data.type !== 'add'"
      data-cy="tx-ref"
      :label="t('common.tx_hash')"
      required
      :hint="txRefHint"
      :error-messages="toMessages(v$.txRef)"
      @blur="v$.txRef.$touch()"
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
          data-cy="tx-ref-loading"
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
              data-cy="tx-ref-retry"
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

    <SwapSubEventList
      ref="spendListRef"
      v-model="states.spend"
      data-cy="spend"
      :location="states.location"
      :timestamp="timestamp"
      type="spend"
    />

    <RuiDivider class="mb-6 mt-2" />

    <SwapSubEventList
      ref="receiveListRef"
      v-model="states.receive"
      data-cy="receive"
      :location="states.location"
      :timestamp="timestamp"
      type="receive"
    />

    <RuiDivider class="mb-6 mt-2" />

    <RuiCheckbox
      v-model="hasFee"
      :label="t('transactions.events.form.has_fee.label')"
      data-cy="has-fee"
      color="primary"
    />

    <SwapSubEventList
      ref="feeListRef"
      v-model="states.fee"
      data-cy="fee"
      :location="states.location"
      :disabled="!hasFee"
      :timestamp="timestamp"
      type="fee"
    />

    <RuiDivider class="mb-6 mt-2" />

    <RuiTextField
      v-model="states.address"
      clearable
      variant="outlined"
      data-cy="address"
      :label="t('transactions.events.form.contract_address.label')"
      :error-messages="toMessages(v$.address)"
      @blur="v$.address.$touch()"
    />

    <div class="grid md:grid-cols-2 gap-4">
      <AmountInput
        v-model="states.sequenceIndex"
        variant="outlined"
        integer
        :disabled="data.type === 'edit-group'"
        data-cy="sequence-index"
        :label="t('transactions.events.form.sequence_index.label')"
        required
        :error-messages="toMessages(v$.sequenceIndex)"
        @blur="v$.sequenceIndex.$touch()"
      />

      <CounterpartyInput
        v-model="states.counterparty"
        :label="t('common.counterparty')"
        data-cy="counterparty"
        :error-messages="toMessages(v$.counterparty)"
        @blur="v$.counterparty.$touch()"
      />
    </div>
  </div>
</template>
