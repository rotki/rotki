<script setup lang="ts">
import dayjs from 'dayjs';
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import { helpers, required } from '@vuelidate/validators';
import { Blockchain } from '@rotki/common/lib/blockchain';
import {
  type EthBlockEvent,
  type NewEthBlockEventPayload
} from '@/types/history/events';
import { type Writeable } from '@/types';
import { toMessages } from '@/utils/validation';
import HistoryEventAssetPriceForm from '@/components/history/events/forms/HistoryEventAssetPriceForm.vue';

const props = defineProps<{
  editableItem: EthBlockEvent | null;
  groupHeader: EthBlockEvent | null;
}>();

const { t } = useI18n();

const { editableItem, groupHeader } = toRefs(props);
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const assetPriceForm: Ref<InstanceType<
  typeof HistoryEventAssetPriceForm
> | null> = ref(null);

const datetime: Ref<string> = ref('');
const amount: Ref<string> = ref('');
const usdValue: Ref<string> = ref('');
const blockNumber: Ref<string> = ref('');
const validatorIndex: Ref<string> = ref('');
const feeRecipient: Ref<string> = ref('');
const isMevReward: Ref<boolean> = ref(false);

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
  blockNumber: {
    required: helpers.withMessage(
      t(
        'transactions.events.form.block_number.validation.non_empty'
      ).toString(),
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
  feeRecipient: {
    required: helpers.withMessage(
      t(
        'transactions.events.form.fee_recipient.validation.non_empty'
      ).toString(),
      required
    ),
    isValid: helpers.withMessage(
      t('transactions.events.form.fee_recipient.validation.valid').toString(),
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
    blockNumber,
    validatorIndex,
    feeRecipient
  },
  {
    $autoDirty: true,
    $externalResults: errorMessages
  }
);

const reset = () => {
  set(datetime, convertFromTimestamp(dayjs().unix(), true));
  set(amount, '0');
  set(usdValue, '0');
  set(blockNumber, '');
  set(validatorIndex, '');
  set(feeRecipient, '');
  set(isMevReward, false);
  set(errorMessages, {});

  get(assetPriceForm)?.reset();
};

const applyEditableData = async (entry: EthBlockEvent) => {
  set(datetime, convertFromTimestamp(entry.timestamp, true));
  set(amount, entry.balance.amount.toFixed());
  set(usdValue, entry.balance.usdValue.toFixed());
  set(blockNumber, entry.blockNumber.toString());
  set(validatorIndex, entry.validatorIndex.toString());
  set(feeRecipient, entry.locationLabel);
  set(isMevReward, entry.eventSubtype === 'mev reward');
};

const applyGroupHeaderData = async (entry: EthBlockEvent) => {
  set(feeRecipient, entry.locationLabel ?? '');
  set(blockNumber, entry.blockNumber.toString());
  set(validatorIndex, entry.validatorIndex.toString());
  set(datetime, convertFromTimestamp(entry.timestamp, true));
};

const { setMessage } = useMessageStore();

const { editHistoryEvent, addHistoryEvent } = useHistoryTransactions();

const save = async (): Promise<boolean> => {
  const timestamp = convertToTimestamp(get(datetime));

  const payload: Writeable<NewEthBlockEventPayload> = {
    entryType: HistoryEventEntryType.ETH_BLOCK_EVENT,
    // Change this
    timestamp: timestamp * 1000,
    balance: {
      amount: get(numericAmount).isNaN() ? Zero : get(numericAmount),
      usdValue: get(numericUsdValue).isNaN() ? Zero : get(numericUsdValue)
    },
    blockNumber: parseInt(get(blockNumber)),
    validatorIndex: parseInt(get(validatorIndex)),
    feeRecipient: get(feeRecipient),
    isMevReward: get(isMevReward)
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

const feeRecipientSuggestions = computed(() =>
  get(accounts)
    .filter(item => item.chain === Blockchain.ETH)
    .map(item => item.address)
);
</script>

<template>
  <div>
    <div class="grid md:grid-cols-3 gap-4">
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
        v-model="blockNumber"
        :disabled="!!(editableItem || groupHeader)"
        outlined
        required
        integer
        data-cy="blockNumber"
        :label="t('transactions.events.form.block_number.label')"
        :error-messages="toMessages(v$.blockNumber)"
        @blur="v$.blockNumber.$touch()"
      />
      <AmountInput
        v-model="validatorIndex"
        :disabled="!!(editableItem || groupHeader)"
        outlined
        required
        integer
        data-cy="validatorIndex"
        :label="t('transactions.events.form.validator_index.label')"
        :error-messages="toMessages(v$.validatorIndex)"
        @blur="v$.validatorIndex.$touch()"
      />
    </div>

    <div class="border-t mb-6 mt-2" />

    <HistoryEventAssetPriceForm
      ref="assetPriceForm"
      asset="ETH"
      :v$="v$"
      :datetime="datetime"
      :amount.sync="amount"
      :usd-value.sync="usdValue"
      disable-asset
    />

    <div class="border-t my-10" />

    <ComboboxWithCustomInput
      v-model="feeRecipient"
      :items="feeRecipientSuggestions"
      :disabled="!!(editableItem || groupHeader)"
      outlined
      data-cy="feeRecipient"
      :label="t('transactions.events.form.fee_recipient.label')"
      :error-messages="toMessages(v$.feeRecipient)"
      auto-select-first
      @blur="v$.feeRecipient.$touch()"
    />

    <RuiCheckbox v-model="isMevReward" color="primary">
      {{ t('transactions.events.form.is_mev_reward.label') }}
    </RuiCheckbox>
  </div>
</template>
