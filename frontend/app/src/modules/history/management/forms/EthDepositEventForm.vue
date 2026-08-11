<script setup lang="ts">
import type { EthDepositEvent } from '@/modules/history/events/schemas';
import type { StandaloneEventData } from '@/modules/history/management/forms/form-types';
import { Blockchain } from '@rotki/common';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { EVENT_PRICE_INTENT_KEYS } from '@/modules/history/management/forms/eth-block-event-form';
import {
  emptyEthDepositForm,
  ethDepositSchema,
  ethDepositStateFromEvent,
  ethDepositStateFromGroup,
  toEthDepositPayload,
} from '@/modules/history/management/forms/eth-deposit-event-form';
import HistoryEventAssetPriceForm from '@/modules/history/management/forms/HistoryEventAssetPriceForm.vue';
import { useEvmTxAutoFill } from '@/modules/history/management/forms/use-evm-tx-lookup';
import { useHistoryEventForm } from '@/modules/history/management/forms/use-history-event-form';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';
import AutoCompleteWithSearchSync from '@/modules/shell/components/inputs/AutoCompleteWithSearchSync.vue';
import DateTimePicker from '@/modules/shell/components/inputs/DateTimePicker.vue';
import JsonInput from '@/modules/shell/components/inputs/JsonInput.vue';

interface EthDepositEventFormProps {
  data: StandaloneEventData<EthDepositEvent>;
}

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { data } = defineProps<EthDepositEventFormProps>();

const { t } = useI18n({ useScope: 'global' });

// Shared with the transaction lookup below, which reports its failures as field errors too.
const errorMessages = ref<Record<string, string[]>>({});

const { getAddresses } = useAccountAddresses();

const { form, save, seed } = useHistoryEventForm({
  errorMessages,
  initial: () => emptyEthDepositForm(data.nextSequenceId),
  priceIntentKeys: EVENT_PRICE_INTENT_KEYS,
  priceIntents: state => (state.priceIntent ? [state.priceIntent] : []),
  schema: computed(() => ethDepositSchema(data.type === 'edit')),
  stateUpdated,
  toEditPayload: (payload, identifiers) => ({ ...payload, identifier: identifiers[0] }),
  transform: toEthDepositPayload,
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
  errorFields: { relatedAddress: 'depositor', txHash: 'txRef' },
  errorMessages,
  evmChain: 'ethereum',
  onResolved: (result) => {
    state.timestamp = result.timestamp * 1000;
  },
  relatedAddress: () => state.depositor,
  txHash: () => state.txRef,
});

const txRefHint = computed<string>(() => {
  if (get(lookupLoading))
    return t('actions.evm_tx_lookup.loading');
  if (get(lookupNeedsRelatedAddress))
    return t('actions.evm_tx_lookup.needs_related_address');
  return '';
});

const depositorSuggestions = computed<string[]>(() => getAddresses(Blockchain.ETH));

watchImmediate(() => data, (data) => {
  resetLookup();

  if (data.type === 'edit') {
    seed(ethDepositStateFromEvent(data.event), [data.event.identifier]);
    return;
  }

  seed(data.type === 'group-add'
    ? ethDepositStateFromGroup(data.group, data.nextSequenceId)
    : emptyEthDepositForm(data.nextSequenceId));
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
      <AmountInput
        v-model="state.validatorIndex"
        variant="outlined"
        integer
        data-testid="validatorIndex"
        :label="t('transactions.events.form.validator_index.label')"
        required
        :error-messages="form.errors('validatorIndex')"
        @blur="form.touch('validatorIndex')"
      />
    </div>

    <RuiTextField
      v-model="state.txRef"
      variant="outlined"
      color="primary"
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
      v-model:amount="state.amount"
      v-model:price-intent="state.priceIntent"
      asset="ETH"
      :error-messages="{ amount: form.errors('amount') }"
      :timestamp="state.timestamp"
      location="ethereum"
      disable-asset
      @blur="form.touch('amount')"
    />

    <RuiDivider class="mb-6" />

    <div class="grid md:grid-cols-2 gap-4">
      <AutoCompleteWithSearchSync
        v-model="state.depositor"
        :items="depositorSuggestions"
        data-testid="depositor"
        :label="t('transactions.events.form.depositor.label')"
        required
        :error-messages="form.errors('depositor')"
        auto-select-first
        @blur="form.touch('depositor')"
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

    <RuiDivider class="mb-2 mt-6" />

    <RuiAccordions>
      <RuiAccordion
        data-testid="eth-deposit-event-form__advance"
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
