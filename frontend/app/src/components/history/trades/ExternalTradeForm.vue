<script setup lang="ts">
import type { ValidationErrors } from '@/types/api/errors';
import type { Trade } from '@/types/history/trade';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import AmountInput from '@/components/inputs/AmountInput.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import DateTimePicker from '@/components/inputs/DateTimePicker.vue';
import TwoFieldsAmountInput from '@/components/inputs/TwoFieldsAmountInput.vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useFormStateWatcher } from '@/composables/form';
import { refIsTruthy } from '@/composables/ref';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { bigNumberifyFromRef } from '@/utils/bignumbers';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';
import { refOptional, useBigNumberModel, useRefPropVModel } from '@/utils/model';
import { toMessages } from '@/utils/validation';
import useVuelidate from '@vuelidate/core';
import { helpers, required, requiredIf } from '@vuelidate/validators';

const modelValue = defineModel<Trade>({ required: true });
const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });

const props = defineProps<{
  editMode: boolean;
}>();

const { t } = useI18n();

const { useIsTaskRunning } = useTaskStore();
const { getHistoricPrice } = useBalancePricesStore();

const base = useRefPropVModel(modelValue, 'baseAsset');
const quote = useRefPropVModel(modelValue, 'quoteAsset');
const amount = useRefPropVModel(modelValue, 'amount');
const rate = useRefPropVModel(modelValue, 'rate');
const fee = useRefPropVModel(modelValue, 'fee');
const feeCurrency = useRefPropVModel(modelValue, 'feeCurrency');
const link = useRefPropVModel(modelValue, 'link');
const notes = useRefPropVModel(modelValue, 'notes');
const type = useRefPropVModel(modelValue, 'tradeType');
const timestamp = useRefPropVModel(modelValue, 'timestamp');

const amountModel = useBigNumberModel(amount);
const feeModel = useBigNumberModel(fee);
const rateModel = useBigNumberModel(rate);

const notesModel = refOptional(notes, '');
const linkModel = refOptional(link, '');
const feeCurrencyModel = refOptional(feeCurrency, '');

const quoteAmount = ref('');

const numericQuoteAmount = bigNumberifyFromRef(quoteAmount);

const datetime = computed({
  get: () => convertFromTimestamp(get(timestamp)),
  set: (value: string) => {
    set(timestamp, convertToTimestamp(value));
  },
});

const quoteAmountInputFocused = ref<boolean>(false);
const feeInput = ref<any>(null);
const feeCurrencyInput = ref<any>(null);

const { assetSymbol } = useAssetInfoRetrieval();
const baseSymbol = assetSymbol(base);
const quoteSymbol = assetSymbol(quote);

const externalServerValidation = () => true;

const rules = {
  amount: {
    required: helpers.withMessage(t('external_trade_form.validation.non_empty_amount'), required),
  },
  baseAsset: {
    required: helpers.withMessage(t('external_trade_form.validation.non_empty_base'), required),
  },
  fee: {
    required: helpers.withMessage(t('external_trade_form.validation.non_empty_fee'), requiredIf(refIsTruthy(feeCurrency))),
  },
  feeCurrency: {
    required: helpers.withMessage(t('external_trade_form.validation.non_empty_fee_currency'), requiredIf(refIsTruthy(feeModel))),
  },
  quoteAmount: { externalServerValidation },
  quoteAsset: {
    required: helpers.withMessage(t('external_trade_form.validation.non_empty_quote'), required),
  },
  rate: {
    required: helpers.withMessage(t('external_trade_form.validation.non_empty_rate'), required),
  },
  timestamp: { externalServerValidation },
};

const states = {
  amount: amountModel,
  baseAsset: base,
  fee: feeModel,
  feeCurrency,
  quoteAmount,
  quoteAsset: quote,
  rate: rateModel,
  timestamp: datetime,
};

const v$ = useVuelidate(rules, states, {
  $autoDirty: true,
  $externalResults: errors,
});

useFormStateWatcher(states, stateUpdated);

function triggerFeeValidator() {
  get(feeInput)?.textInput?.validate(true);
  get(feeCurrencyInput)?.autoCompleteInput?.validate(true);
}

const quoteHint = computed<string>(() => (get(type) === 'buy' ? t('external_trade_form.buy_quote') : t('external_trade_form.sell_quote')));

const shouldRenderSummary = computed<boolean>(() => !!(get(type) && get(base) && get(quote) && get(amountModel) && get(rateModel)));

const fetching = useIsTaskRunning(TaskType.FETCH_HISTORIC_PRICE);

function updateRate(forceUpdate = false) {
  if (get(amount) && get(rate) && (!get(quoteAmountInputFocused) || forceUpdate))
    set(quoteAmount, get(amount).multipliedBy(get(rate)).toFixed());
}

async function fetchPrice() {
  if ((get(rate) && props.editMode) || !get(datetime) || !get(base) || !get(quote))
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
    set(rate, rateFromHistoricPrice);
    updateRate(true);
  }
  else if (!get(rate)) {
    set(errors, {
      ...get(errors),
      rate: [t('external_trade_form.rate_not_found')],
    });
    await get(v$).rate.$validate();
    useTimeoutFn(() => {
      set(errors, {});
    }, 4000);
  }
}

function onQuoteAmountChange() {
  if (get(amount) && get(quoteAmount) && get(quoteAmountInputFocused))
    set(rate, get(numericQuoteAmount).div(get(amount)));
}

watch([timestamp, quote, base], async () => {
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

defineExpose({
  validate: () => get(v$).$validate(),
});
</script>

<template>
  <form
    data-cy="trade-form"
    class="external-trade-form"
  >
    <DateTimePicker
      v-model="timestamp"
      limit-now
      data-cy="date"
      :label="t('common.datetime')"
      persistent-hint
      :hint="t('external_trade_form.date.hint')"
      :error-messages="toMessages(v$.timestamp)"
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
        v-model="amountModel"
        variant="outlined"
        class="mb-2"
        :error-messages="toMessages(v$.amount)"
        data-cy="amount"
        :label="t('common.amount')"
        :hint="t('external_trade_form.amount.hint')"
        @blur="v$.amount.$touch()"
      />
      <TwoFieldsAmountInput
        v-model:primary-value="rateModel"
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
          name="lu-message-square-quote"
        />
        <i18n-t
          v-if="type === 'buy'"
          keypath="external_trade_form.summary.buy"
        >
          <template #label>
            <strong>{{ t("external_trade_form.summary.label") }}</strong>
          </template>
          <template #amount>
            <strong>
              <AmountDisplay
                :value="amount"
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
                :value="rate"
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
            <strong>{{ t("external_trade_form.summary.label") }}</strong>
          </template>
          <template #amount>
            <strong>
              <AmountDisplay
                :value="amount"
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
                :value="rate"
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
        v-model="feeModel"
        class="external-trade-form__fee"
        variant="outlined"
        data-cy="fee"
        :required="!!feeCurrency"
        :label="t('common.fee')"
        :hint="t('external_trade_form.fee.hint')"
        :error-messages="toMessages(v$.fee)"
        @update:model-value="triggerFeeValidator()"
      />
      <AssetSelect
        ref="feeCurrencyInput"
        v-model="feeCurrencyModel"
        data-cy="fee-currency"
        outlined
        :label="t('external_trade_form.fee_currency.label')"
        :hint="t('external_trade_form.fee_currency.hint')"
        :error-messages="toMessages(v$.feeCurrency)"
        @update:model-value="triggerFeeValidator()"
      />
    </div>

    <RuiTextField
      v-model="linkModel"
      data-cy="link"
      variant="outlined"
      color="primary"
      prepend-icon="lu-link-2"
      :label="t('external_trade_form.link.label')"
      :hint="t('external_trade_form.link.hint')"
      :error-messages="errorMessages.link"
    />

    <RuiTextArea
      v-model="notesModel"
      prepend-icon="lu-sticky-note"
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
