<script setup lang="ts">
import type { EthWithdrawalEvent } from '@/modules/history/events/schemas';
import type { StandaloneEventData } from '@/modules/history/management/forms/form-types';
import { Blockchain } from '@rotki/common';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { EVENT_PRICE_INTENT_KEYS } from '@/modules/history/management/forms/eth-block-event-form';
import {
  emptyEthWithdrawalForm,
  ethWithdrawalSchema,
  ethWithdrawalStateFromEvent,
  ethWithdrawalStateFromGroup,
  toEthWithdrawalPayload,
} from '@/modules/history/management/forms/eth-withdrawal-event-form';
import HistoryEventAssetPriceForm from '@/modules/history/management/forms/HistoryEventAssetPriceForm.vue';
import { useHistoryEventForm } from '@/modules/history/management/forms/use-history-event-form';
import AmountInput from '@/modules/shell/components/inputs/AmountInput.vue';
import AutoCompleteWithSearchSync from '@/modules/shell/components/inputs/AutoCompleteWithSearchSync.vue';
import DateTimePicker from '@/modules/shell/components/inputs/DateTimePicker.vue';

interface EthWithdrawalEventFormProps {
  data: StandaloneEventData<EthWithdrawalEvent>;
}

const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const { data } = defineProps<EthWithdrawalEventFormProps>();

const { t } = useI18n({ useScope: 'global' });

const { getAddresses } = useAccountAddresses();

const { form, save, seed } = useHistoryEventForm({
  initial: emptyEthWithdrawalForm,
  priceIntentKeys: EVENT_PRICE_INTENT_KEYS,
  priceIntents: state => (state.priceIntent ? [state.priceIntent] : []),
  schema: computed(() => ethWithdrawalSchema(data.type === 'edit')),
  stateUpdated,
  toEditPayload: (payload, identifiers) => ({ ...payload, identifier: identifiers[0] }),
  transform: toEthWithdrawalPayload,
});

const { state } = form;

const withdrawalAddressSuggestions = computed<string[]>(() => getAddresses(Blockchain.ETH));

watchImmediate(() => data, (data) => {
  if (data.type === 'edit') {
    seed(ethWithdrawalStateFromEvent(data.event), [data.event.identifier]);
    return;
  }

  seed(data.type === 'group-add' ? ethWithdrawalStateFromGroup(data.group) : emptyEthWithdrawalForm());
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
      v-model="state.withdrawalAddress"
      :items="withdrawalAddressSuggestions"
      data-testid="withdrawal-address"
      :label="t('transactions.events.form.withdrawal_address.label')"
      required
      :error-messages="form.errors('withdrawalAddress')"
      auto-select-first
      @blur="form.touch('withdrawalAddress')"
    />

    <RuiCheckbox
      v-model="state.isExit"
      color="primary"
      data-testid="is-exit"
    >
      {{ t('transactions.events.form.is_exit.label') }}
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
