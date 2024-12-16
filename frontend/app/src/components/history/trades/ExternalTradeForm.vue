<script setup lang="ts">
import { helpers, required, requiredIf } from '@vuelidate/validators';
import dayjs from 'dayjs';
import { TaskType } from '@/types/task-type';
import { toMessages } from '@/utils/validation';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';
import { bigNumberifyFromRef } from '@/utils/bignumbers';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useMessageStore } from '@/store/message';
import { useTaskStore } from '@/store/tasks';
import { useTradesForm } from '@/composables/history/trades/form';
import { useTrades } from '@/composables/history/trades';
import { refIsTruthy } from '@/composables/ref';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import AmountInput from '@/components/inputs/AmountInput.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import TwoFieldsAmountInput from '@/components/inputs/TwoFieldsAmountInput.vue';
import DateTimePicker from '@/components/inputs/DateTimePicker.vue';
import type { NewTrade, Trade, TradeType } from '@/types/history/trade';
import type { Writeable } from '@rotki/common';

const props = withDefaults(
  defineProps<{
    editableItem?: Trade | null;
  }>(),
  {
    editableItem: null,
  },
);

const { t } = useI18n();
const { editableItem } = toRefs(props);

const { isTaskRunning } = useTaskStore();
const { getHistoricPrice } = useBalancePricesStore();

const id = ref<string>('');
const base = ref<string>('');
const quote = ref<string>('');
const datetime = ref<string>('');
const amount = ref<string>('');
const rate = ref<string>('');
const quoteAmount = ref<string>('');
const fee = ref<string>('');
const feeCurrency = ref<string>('');
const link = ref<string>('');
const notes = ref<string>('');
const type = ref<TradeType>('buy');

const errorMessages = ref<Record<string, string[]>>({});

const quoteAmountInputFocused = ref<boolean>(false);
const feeInput = ref<any>(null);
const feeCurrencyInput = ref<any>(null);

const { assetSymbol } = useAssetInfoRetrieval();
const baseSymbol = assetSymbol(base);
const quoteSymbol = assetSymbol(quote);

const rules = {
  amount: {
    required: helpers.withMessage(t('external_trade_form.validation.non_empty_amount'), required),
  },
  baseAsset: {
    required: helpers.withMessage(t('external_trade_form.validation.non_empty_base'), required),
  },
  fee: {
    required: helpers.withMessage(
      t('external_trade_form.validation.non_empty_fee'),
      requiredIf(refIsTruthy(feeCurrency)),
    ),
  },
  feeCurrency: {
    required: helpers.withMessage(
      t('external_trade_form.validation.non_empty_fee_currency'),
      requiredIf(refIsTruthy(fee)),
    ),
  },
  quoteAmount: {
    required: helpers.withMessage(t('external_trade_form.validation.non_empty_quote_amount'), required),
  },
  quoteAsset: {
    required: helpers.withMessage(t('external_trade_form.validation.non_empty_quote'), required),
  },
  rate: {
    required: helpers.withMessage(t('external_trade_form.validation.non_empty_rate'), required),
  },
};

const { setSubmitFunc, setValidation } = useTradesForm();

const v$ = setValidation(
  rules,
  {
    amount,
    baseAsset: base,
    fee,
    feeCurrency,
    quoteAmount,
    quoteAsset: quote,
    rate,
  },
  {
    $autoDirty: true,
    $externalResults: errorMessages,
  },
);

function triggerFeeValidator() {
  get(feeInput)?.textInput?.validate(true);
  get(feeCurrencyInput)?.autoCompleteInput?.validate(true);
}

const quoteHint = computed<string>(() =>
  get(type) === 'buy' ? t('external_trade_form.buy_quote') : t('external_trade_form.sell_quote'),
);

const shouldRenderSummary = computed<boolean>(
  () => !!(get(type) && get(base) && get(quote) && get(amount) && get(rate)),
);

const fetching = isTaskRunning(TaskType.FETCH_HISTORIC_PRICE);

const numericAmount = bigNumberifyFromRef(amount);
const numericQuoteAmount = bigNumberifyFromRef(quoteAmount);
const numericFee = bigNumberifyFromRef(fee);
const numericRate = bigNumberifyFromRef(rate);

function reset() {
  set(id, '');
  set(datetime, convertFromTimestamp(dayjs().unix()));
  set(amount, '');
  set(rate, '');
  set(fee, '');
  set(feeCurrency, '');
  set(link, '');
  set(notes, '');
  set(type, 'buy');
  set(errorMessages, {});
}

function setEditMode() {
  const trade = get(editableItem);
  if (!trade) {
    reset();
    return;
  }

  set(base, trade.baseAsset);
  set(quote, trade.quoteAsset);
  set(datetime, convertFromTimestamp(trade.timestamp));
  set(amount, trade.amount.toFixed());
  set(rate, trade.rate.toFixed());
  set(fee, trade.fee?.toFixed() ?? '');
  set(feeCurrency, trade.feeCurrency ?? '');
  set(link, trade.link ?? '');
  set(notes, trade.notes ?? '');
  set(type, trade.tradeType);
  set(id, trade.tradeId);
}

const { setMessage } = useMessageStore();

const { addExternalTrade, editExternalTrade } = useTrades();

async function save(): Promise<boolean> {
  const amount = get(numericAmount);
  const fee = get(numericFee);
  const rate = get(numericRate);

  const tradePayload: Writeable<NewTrade> = {
    amount: amount.isNaN() ? Zero : amount,
    baseAsset: get(base),
    fee: fee.isNaN() || fee.isZero() ? null : fee,
    feeCurrency: get(feeCurrency) || null,
    link: get(link) || null,
    location: 'external',
    notes: get(notes) || null,
    quoteAsset: get(quote),
    rate: rate.isNaN() ? Zero : rate,
    timestamp: convertToTimestamp(get(datetime)),
    tradeType: get(type),
  };

  const identifier = get(id);
  const result = !identifier
    ? await addExternalTrade(tradePayload)
    : await editExternalTrade({ ...tradePayload, tradeId: identifier });

  if (result.success) {
    reset();
    return true;
  }

  if (result.message) {
    if (typeof result.message === 'string') {
      setMessage({
        description: result.message,
      });
    }
    else {
      set(errorMessages, result.message);
      await get(v$).$validate();
    }
  }

  return false;
}

setSubmitFunc(save);

function updateRate(forceUpdate = false) {
  if (get(amount) && get(rate) && (!get(quoteAmountInputFocused) || forceUpdate))
    set(quoteAmount, get(numericAmount).multipliedBy(get(numericRate)).toFixed());
}

async function fetchPrice() {
  if ((get(rate) && get(editableItem)) || !get(datetime) || !get(base) || !get(quote))
    return;

  const timestamp = convertToTimestamp(get(datetime));
  const fromAsset = get(base);
  const toAsset = get(quote);

  const rateFromHistoricPrice = await getHistoricPrice({
    fromAsset,
    timestamp,
    toAsset,
  });

  if (rateFromHistoricPrice.gt(0)) {
    set(rate, rateFromHistoricPrice.toFixed());
    updateRate(true);
  }
  else if (!get(rate)) {
    set(errorMessages, {
      rate: [t('external_trade_form.rate_not_found')],
    });
    await get(v$).rate.$validate();
    useTimeoutFn(() => {
      set(errorMessages, {});
    }, 4000);
  }
}

function onQuoteAmountChange() {
  if (get(amount) && get(quoteAmount) && get(quoteAmountInputFocused))
    set(rate, get(numericQuoteAmount).div(get(numericAmount)).toFixed());
}

watch([datetime, quote, base], async () => {
  await fetchPrice();
});

watch(rate, () => {
  updateRate();
});

watch(amount, () => {
  updateRate();
  onQuoteAmountChange();
});

watch(quoteAmount, () => {
  onQuoteAmountChange();
});

watch(editableItem, setEditMode);
onMounted(setEditMode);
</script>

<template>
  <form
    data-cy="trade-form"
    class="external-trade-form"
  >
    <DateTimePicker
      v-model="datetime"
      limit-now
      data-cy="date"
      :label="t('common.datetime')"
      persistent-hint
      :hint="t('external_trade_form.date.hint')"
      :error-messages="errorMessages.timestamp"
    />

    <div class="grid md:grid-cols-4 gap-x-4 gap-y-2">
      <div data-cy="type">
        <RuiRadioGroup
          v-model="type"
          class="pt-3"
          color="primary"
          hide-details
          inline
          required
          :label="t('external_trade_form.trade_type.label')"
        >
          <RuiRadio
            :label="t('external_trade_form.trade_type.buy')"
            value="buy"
            data-cy="trade-input-buy"
          />
          <RuiRadio
            :label="t('external_trade_form.trade_type.sell')"
            value="sell"
            data-cy="trade-input-sell"
          />
        </RuiRadioGroup>
      </div>
      <div class="col-span-3 flex flex-col md:flex-row md:items-start gap-x-4 pt-4">
        <AssetSelect
          v-model="base"
          class="flex-1"
          outlined
          data-cy="base-asset"
          :error-messages="toMessages(v$.baseAsset)"
          :hint="t('external_trade_form.base_asset.hint')"
          :label="t('external_trade_form.base_asset.label')"
          @blur="v$.baseAsset.$touch()"
        />
        <div class="text-rui-text-secondary md:mt-4 mb-4">
          {{ quoteHint }}
        </div>
        <AssetSelect
          v-model="quote"
          class="flex-1"
          outlined
          data-cy="quote-asset"
          :error-messages="toMessages(v$.quoteAsset)"
          :hint="t('external_trade_form.quote_asset.hint')"
          :label="t('external_trade_form.quote_asset.label')"
          @blur="v$.quoteAsset.$touch()"
        />
      </div>
    </div>

    <div class="mt-2">
      <AmountInput
        v-model="amount"
        variant="outlined"
        class="mb-2"
        :error-messages="toMessages(v$.amount)"
        data-cy="amount"
        :label="t('common.amount')"
        :hint="t('external_trade_form.amount.hint')"
        @blur="v$.amount.$touch()"
      />
      <TwoFieldsAmountInput
        v-model:primary-value="rate"
        v-model:secondary-value="quoteAmount"
        class="-mb-5"
        :loading="fetching"
        :disabled="fetching"
        data-cy="trade-rate"
        :label="{
          primary: t('external_trade_form.rate.label'),
          secondary: t('external_trade_form.quote_amount.label'),
        }"
        :error-messages="{
          primary: toMessages(v$.rate),
          secondary: toMessages(v$.quoteAmount),
        }"
        @update:reversed="quoteAmountInputFocused = $event"
      />
      <div
        v-if="shouldRenderSummary"
        class="flex items-center gap-1 text-caption text-rui-success -mt-5 -mb-5 ml-3"
      >
        <RuiIcon
          size="16"
          name="chat-quote-line"
        />
        <i18n-t
          v-if="type === 'buy'"
          keypath="external_trade_form.summary.buy"
        >
          <template #label>
            <strong>{{ t('external_trade_form.summary.label') }}</strong>
          </template>
          <template #amount>
            <strong>
              <AmountDisplay
                :value="numericAmount"
                :tooltip="false"
              />
            </strong>
          </template>
          <template #base>
            <strong>{{ baseSymbol }}</strong>
          </template>
          <template #quote>
            <strong>{{ quoteSymbol }}</strong>
          </template>
          <template #rate>
            <strong>
              <AmountDisplay
                :value="numericRate"
                :tooltip="false"
              />
            </strong>
          </template>
        </i18n-t>
        <i18n-t
          v-if="type === 'sell'"
          tag="span"
          keypath="external_trade_form.summary.sell"
        >
          <template #label>
            <strong>{{ t('external_trade_form.summary.label') }}</strong>
          </template>
          <template #amount>
            <strong>
              <AmountDisplay
                :value="numericAmount"
                :tooltip="false"
              />
            </strong>
          </template>
          <template #base>
            <strong>{{ baseSymbol }}</strong>
          </template>
          <template #quote>
            <strong>{{ quoteSymbol }}</strong>
          </template>
          <template #rate>
            <strong>
              <AmountDisplay
                :value="numericRate"
                :tooltip="false"
              />
            </strong>
          </template>
        </i18n-t>
      </div>
    </div>

    <RuiDivider class="mb-6 mt-8" />

    <div class="grid md:grid-cols-2 gap-x-4 gap-y-2 mb-2">
      <AmountInput
        ref="feeInput"
        v-model="fee"
        class="external-trade-form__fee"
        variant="outlined"
        data-cy="fee"
        :required="!!feeCurrency"
        :label="t('common.label')"
        :hint="t('external_trade_form.fee.hint')"
        :error-messages="toMessages(v$.fee)"
        @update:model-value="triggerFeeValidator()"
      />
      <AssetSelect
        ref="feeCurrencyInput"
        v-model="feeCurrency"
        data-cy="fee-currency"
        outlined
        :label="t('external_trade_form.fee_currency.label')"
        :hint="t('external_trade_form.fee_currency.hint')"
        :error-messages="toMessages(v$.feeCurrency)"
        @update:model-value="triggerFeeValidator()"
      />
    </div>

    <RuiTextField
      v-model="link"
      data-cy="link"
      variant="outlined"
      color="primary"
      prepend-icon="link"
      :label="t('external_trade_form.link.label')"
      :hint="t('external_trade_form.link.hint')"
      :error-messages="errorMessages.link"
    />

    <RuiTextArea
      v-model="notes"
      prepend-icon="sticky-note-line"
      variant="outlined"
      color="primary"
      min-rows="5"
      data-cy="notes"
      class="mt-4"
      :label="t('external_trade_form.notes.label')"
      :hint="t('external_trade_form.notes.hint')"
      :error-messages="errorMessages.notes"
    />
  </form>
</template>
