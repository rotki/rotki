<script lang="ts" setup>
import type { EvmHistoryEvent, EvmSwapEvent } from '@/modules/history/events/schemas';
import type { GroupEventData, StandaloneEventData } from '@/modules/history/management/forms/form-types';
import { toSnakeCase } from '@rotki/common';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import CounterpartyInput from '@/modules/history/events/mapping/CounterpartyInput.vue';
import EventDateLocation from '@/modules/history/management/forms/common/EventDateLocation.vue';
import {
  emptyEvmSwapForm,
  evmSwapSchema,
  evmSwapStateFromEvents,
  toEvmSwapPayload,
} from '@/modules/history/management/forms/evm-swap-event-form';
import { emptySubEvent } from '@/modules/history/management/forms/swap/swap-sub-event';
import SwapSubEventList from '@/modules/history/management/forms/swap/SwapSubEventList.vue';
import { useEvmTxAutoFill } from '@/modules/history/management/forms/use-evm-tx-lookup';
import { useSwapEventForm } from '@/modules/history/management/forms/use-swap-event-form';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { data } = defineProps<{ data: StandaloneEventData<EvmHistoryEvent> | GroupEventData<EvmSwapEvent> }>();

const { t } = useI18n({ useScope: 'global' });

// Shared with the transaction lookup below, which reports its failures as field errors too.
const errorMessages = ref<Record<string, string[]>>({});

const { txChainsToLocation } = useSupportedChains();

const { form, save, seed } = useSwapEventForm({
  errorMessages,
  initial: emptyEvmSwapForm,
  schema: evmSwapSchema(),
  stateUpdated,
  transform: toEvmSwapPayload,
});

const { state } = form;

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
  evmChain: () => toSnakeCase(state.location),
  onResolved: (result) => {
    state.timestamp = result.timestamp * 1000;
  },
  // Use the first spend sub-event's locationLabel as the user's tracked address.
  relatedAddress: () => state.spend[0]?.locationLabel ?? '',
  txHash: () => state.txRef,
});

const txRefHint = computed<string>(() => {
  if (get(lookupLoading))
    return t('actions.evm_tx_lookup.loading');
  if (get(lookupNeedsRelatedAddress))
    return t('actions.evm_tx_lookup.needs_related_address_swap');
  return '';
});

watchImmediate(() => data, (data) => {
  resetLookup();
  if (data.type === 'group-add') {
    const group = data.group;

    seed({
      ...emptyEvmSwapForm(),
      location: group.location ?? '',
      sequenceIndex: data.nextSequenceId.toString(),
      timestamp: group.timestamp,
      txRef: group.txRef,
    });
  }
  else if (data.type === 'edit-group') {
    seed(evmSwapStateFromEvents(data.eventsInGroup), data.eventsInGroup.map(item => item.identifier));
  }
});

watch(() => state.hasFee, (hasFee) => {
  if (!hasFee) {
    state.fee = [];
    return;
  }

  // Seeding an existing group sets the flag and the rows together, so only an empty list wants a
  // blank row; replacing it unconditionally would discard what was just loaded.
  if (state.fee.length === 0)
    state.fee.push(emptySubEvent());
});

defineExpose({
  errorCount: form.errorCount,
  save,
});
</script>

<template>
  <div>
    <EventDateLocation
      v-model:timestamp="state.timestamp"
      v-model:location="state.location"
      :location-disabled="data.type !== 'add'"
      :locations="txChainsToLocation"
      :error-messages="{
        location: form.errors('location'),
        timestamp: form.errors('timestamp'),
      }"
      @blur="form.touch($event)"
    />

    <RuiDivider class="mb-6 mt-2" />

    <RuiTextField
      v-model="state.txRef"
      variant="outlined"
      color="primary"
      :disabled="data.type !== 'add'"
      data-cy="tx-ref"
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
      v-model="state.spend"
      data-cy="spend"
      path="spend"
      :errors="form.errors"
      :touch="form.touch"
      :location="state.location"
      :timestamp="state.timestamp"
      type="spend"
    />

    <RuiDivider class="mb-6 mt-2" />

    <SwapSubEventList
      v-model="state.receive"
      data-cy="receive"
      path="receive"
      :errors="form.errors"
      :touch="form.touch"
      :location="state.location"
      :timestamp="state.timestamp"
      type="receive"
    />

    <RuiDivider class="mb-6 mt-2" />

    <RuiCheckbox
      v-model="state.hasFee"
      :label="t('transactions.events.form.has_fee.label')"
      data-cy="has-fee"
      color="primary"
    />

    <SwapSubEventList
      v-model="state.fee"
      data-cy="fee"
      path="fee"
      :errors="form.errors"
      :touch="form.touch"
      :location="state.location"
      :disabled="!state.hasFee"
      :timestamp="state.timestamp"
      type="fee"
    />

    <RuiDivider class="mb-6 mt-2" />

    <RuiTextField
      v-model="state.address"
      clearable
      variant="outlined"
      data-cy="address"
      :label="t('transactions.events.form.contract_address.label')"
      :error-messages="form.errors('address')"
      @blur="form.touch('address')"
    />

    <div class="grid md:grid-cols-2 gap-4">
      <AmountInput
        v-model="state.sequenceIndex"
        variant="outlined"
        integer
        :disabled="data.type === 'edit-group'"
        data-cy="sequence-index"
        :label="t('transactions.events.form.sequence_index.label')"
        required
        :error-messages="form.errors('sequenceIndex')"
        @blur="form.touch('sequenceIndex')"
      />

      <CounterpartyInput
        v-model="state.counterparty"
        :label="t('common.counterparty')"
        data-cy="counterparty"
        :error-messages="form.errors('counterparty')"
        @blur="form.touch('counterparty')"
      />
    </div>
  </div>
</template>
