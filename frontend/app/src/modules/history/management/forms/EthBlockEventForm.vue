<script setup lang="ts">
import type { EthBlockEvent } from '@/modules/history/events/schemas';
import type { StandaloneEventData } from '@/modules/history/management/forms/form-types';
import { Blockchain } from '@rotki/common';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import {
  emptyEthBlockForm,
  ethBlockSchema,
  ethBlockStateFromEvent,
  ethBlockStateFromGroup,
  EVENT_PRICE_INTENT_KEYS,
  toEthBlockPayload,
} from '@/modules/history/management/forms/eth-block-event-form';
import HistoryEventAssetPriceForm from '@/modules/history/management/forms/HistoryEventAssetPriceForm.vue';
import { useHistoryEventForm } from '@/modules/history/management/forms/use-history-event-form';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';
import AutoCompleteWithSearchSync from '@/modules/shell/components/inputs/AutoCompleteWithSearchSync.vue';
import DateTimePicker from '@/modules/shell/components/inputs/DateTimePicker.vue';

interface EthBlockEventFormProps {
  data: StandaloneEventData<EthBlockEvent>;
}

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });
const { data } = defineProps<EthBlockEventFormProps>();

const { t } = useI18n({ useScope: 'global' });

const { getAddresses } = useAccountAddresses();

const { form, save, seed } = useHistoryEventForm({
  initial: emptyEthBlockForm,
  priceIntentKeys: EVENT_PRICE_INTENT_KEYS,
  priceIntents: state => (state.priceIntent ? [state.priceIntent] : []),
  schema: computed(() => ethBlockSchema(data.type === 'edit')),
  stateUpdated,
  toEditPayload: (payload, identifiers) => ({ ...payload, identifier: identifiers[0] }),
  transform: toEthBlockPayload,
});

const { state } = form;

const feeRecipientSuggestions = computed<string[]>(() => getAddresses(Blockchain.ETH));

watchImmediate(() => data, (data) => {
  if (data.type === 'edit') {
    seed(ethBlockStateFromEvent(data.event), [data.event.identifier]);
    return;
  }

  seed(data.type === 'group-add' ? ethBlockStateFromGroup(data.group) : emptyEthBlockForm());
});

defineExpose({
  errorCount: form.errorCount,
  save,
});
</script>

<template>
  <div>
    <div class="grid md:grid-cols-4 gap-4 mb-4">
      <DateTimePicker
        v-model="state.timestamp"
        class="md:col-span-2"
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
        v-model="state.blockNumber"
        variant="outlined"
        integer
        data-testid="block-number"
        :label="t('transactions.events.form.block_number.label')"
        required
        :error-messages="form.errors('blockNumber')"
        @blur="form.touch('blockNumber')"
      />
      <AmountInput
        v-model="state.validatorIndex"
        variant="outlined"
        integer
        data-testid="validator-index"
        :label="t('transactions.events.form.validator_index.label')"
        required
        :error-messages="form.errors('validatorIndex')"
        @blur="form.touch('validatorIndex')"
      />
    </div>

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

    <AutoCompleteWithSearchSync
      v-model="state.feeRecipient"
      :items="feeRecipientSuggestions"
      data-testid="fee-recipient"
      :label="t('transactions.events.form.fee_recipient.label')"
      required
      :error-messages="form.errors('feeRecipient')"
      auto-select-first
      @blur="form.touch('feeRecipient')"
    />

    <RuiCheckbox
      v-model="state.isMevReward"
      color="primary"
      data-testid="is-mev-reward"
    >
      {{ t('transactions.events.form.is_mev_reward.label') }}
    </RuiCheckbox>

    <RuiDivider class="mb-2" />

    <RuiAccordions>
      <RuiAccordion
        data-testid="eth-block-event-form__advance"
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
        </div>
      </RuiAccordion>
    </RuiAccordions>
  </div>
</template>
