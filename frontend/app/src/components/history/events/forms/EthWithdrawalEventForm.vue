<script setup lang="ts">
import dayjs from 'dayjs';
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import { helpers, required } from '@vuelidate/validators';
import { Blockchain } from '@rotki/common/lib/blockchain';
import {
  type EthWithdrawalEvent,
  type NewEthWithdrawalEventPayload
} from '@/types/history/events';
import { type Writeable } from '@/types';
import { toMessages } from '@/utils/validation';
import HistoryEventAssetPriceForm from '@/components/history/events/forms/HistoryEventAssetPriceForm.vue';

const props = withDefaults(
  defineProps<{
    editableItem?: EthWithdrawalEvent | null;
    groupHeader?: EthWithdrawalEvent | null;
  }>(),
  {
    editableItem: null,
    groupHeader: null
  }
);

const { t } = useI18n();

const { editableItem, groupHeader } = toRefs(props);
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const assetPriceForm: Ref<InstanceType<
  typeof HistoryEventAssetPriceForm
> | null> = ref(null);

const datetime: Ref<string> = ref('');
const amount: Ref<string> = ref('');
const usdValue: Ref<string> = ref('');
const validatorIndex: Ref<string> = ref('');
const withdrawalAddress: Ref<string> = ref('');
const isExit: Ref<boolean> = ref(false);

const errorMessages = ref<Record<string, string[]>>({});

const rules = {
  timestamp: { externalServerValidation: () => true },
  amount: {
    required: helpers.withMessage(
      t('transactions.events.form.amount.validation.non_empty').toString(),
      required
    )
  },
  usdValue: {
    required: helpers.withMessage(
      t('transactions.events.form.fiat_value.validation.non_empty', {
        currency: get(currencySymbol)
      }).toString(),
      required
    )
  },
  validatorIndex: {
    required: helpers.withMessage(
      t(
        'transactions.events.form.validator_index.validation.non_empty'
      ).toString(),
      required
    )
  },
  withdrawalAddress: {
    required: helpers.withMessage(
      t(
        'transactions.events.form.withdrawal_address.validation.non_empty'
      ).toString(),
      required
    ),
    isValid: helpers.withMessage(
      t(
        'transactions.events.form.withdrawal_address.validation.valid'
      ).toString(),
      (value: string) => isValidEthAddress(value)
    )
  }
};

const { setValidation, setSubmitFunc } = useHistoryEventsForm();

const v$ = setValidation(
  rules,
  {
    timestamp: datetime,
    amount,
    usdValue,
    validatorIndex,
    withdrawalAddress
  },
  {
    $autoDirty: true,
    $externalResults: errorMessages
  }
);

const reset = () => {
  set(datetime, convertFromTimestamp(dayjs().unix()));
  set(amount, '0');
  set(usdValue, '0');
  set(validatorIndex, '');
  set(withdrawalAddress, '');
  set(isExit, false);
  set(errorMessages, {});

  get(assetPriceForm)?.reset();
};

const applyEditableData = async (entry: EthWithdrawalEvent) => {
  set(datetime, convertFromTimestamp(entry.timestamp));
  set(amount, entry.balance.amount.toFixed());
  set(usdValue, entry.balance.usdValue.toFixed());
  set(validatorIndex, entry.validatorIndex.toString());
  set(withdrawalAddress, entry.locationLabel);
  set(isExit, entry.isExit);
};

const applyGroupHeaderData = async (entry: EthWithdrawalEvent) => {
  set(withdrawalAddress, entry.locationLabel ?? '');
  set(validatorIndex, entry.validatorIndex.toString());
  set(datetime, convertFromTimestamp(entry.timestamp));
};

const { setMessage } = useMessageStore();

const { editHistoryEvent, addHistoryEvent } = useHistoryTransactions();

const save = async (): Promise<boolean> => {
  const timestamp = convertToTimestamp(get(datetime));

  const payload: Writeable<NewEthWithdrawalEventPayload> = {
    entryType: HistoryEventEntryType.ETH_WITHDRAWAL_EVENT,
    timestamp: timestamp * 1000,
    balance: {
      amount: get(numericAmount).isNaN() ? Zero : get(numericAmount),
      usdValue: get(numericUsdValue).isNaN() ? Zero : get(numericUsdValue)
    },
    validatorIndex: parseInt(get(validatorIndex)),
    withdrawalAddress: get(withdrawalAddress),
    isExit: get(isExit)
  };

  const submitPriceResult = await get(assetPriceForm)!.submitPrice(payload);

  if (!submitPriceResult.success) {
    set(errorMessages, submitPriceResult.message);
    return false;
  }

  const edit = get(editableItem);
  const result = !edit
    ? await addHistoryEvent(payload)
    : await editHistoryEvent({
        ...payload,
        identifier: edit.identifier
      });

  if (result.success) {
    reset();
    return true;
  }

  if (result.message) {
    if (typeof result.message === 'string') {
      setMessage({
        description: result.message
      });
    } else {
      set(errorMessages, result.message);
      await get(v$).$validate();
    }
  }

  return false;
};

setSubmitFunc(save);

const numericAmount = bigNumberifyFromRef(amount);
const numericUsdValue = bigNumberifyFromRef(usdValue);

const checkPropsData = () => {
  const editable = get(editableItem);
  if (editable) {
    applyEditableData(editable);
    return;
  }
  const group = get(groupHeader);
  if (group) {
    applyGroupHeaderData(group);
    return;
  }
  reset();
};

watch([groupHeader, editableItem], checkPropsData);
onMounted(() => {
  checkPropsData();
});

const { accounts } = useAccountBalances();

const withdrawalAddressSuggestions = computed(() =>
  get(accounts)
    .filter(item => item.chain === Blockchain.ETH)
    .map(item => item.address)
);
</script>

<template>
  <div>
    <div class="grid md:grid-cols-2 gap-4">
      <DateTimePicker
        v-model="datetime"
        outlined
        :label="t('transactions.events.form.datetime.label')"
        persistent-hint
        limit-now
        milliseconds
        data-cy="datetime"
        :hint="t('transactions.events.form.datetime.hint')"
        :error-messages="toMessages(v$.timestamp)"
        @blur="v$.timestamp.$touch()"
      />

      <AmountInput
        v-model="validatorIndex"
        outlined
        required
        integer
        data-cy="validatorIndex"
        :label="t('transactions.events.form.validator_index.label')"
        :error-messages="toMessages(v$.validatorIndex)"
        @blur="v$.validatorIndex.$touch()"
      />
    </div>

    <div class="border-t dark:border-rui-grey-800 mb-6 mt-2" />

    <HistoryEventAssetPriceForm
      ref="assetPriceForm"
      asset="ETH"
      :v$="v$"
      :datetime="datetime"
      :amount.sync="amount"
      :usd-value.sync="usdValue"
      disable-asset
    />

    <div class="border-t dark:border-rui-grey-800 my-10" />

    <ComboboxWithCustomInput
      v-model="withdrawalAddress"
      :items="withdrawalAddressSuggestions"
      outlined
      data-cy="withdrawalAddress"
      :label="t('transactions.events.form.withdrawal_address.label')"
      :error-messages="toMessages(v$.withdrawalAddress)"
      auto-select-first
      @blur="v$.withdrawalAddress.$touch()"
    />

    <RuiCheckbox v-model="isExit" color="primary" data-cy="isExited">
      {{ t('transactions.events.form.is_exit.label') }}
    </RuiCheckbox>
  </div>
</template>
