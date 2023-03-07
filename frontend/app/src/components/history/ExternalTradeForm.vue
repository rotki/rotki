<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, required, requiredIf } from '@vuelidate/validators';
import dayjs from 'dayjs';
import { type PropType } from 'vue';
import { convertKeys } from '@/services/axios-tranformers';
import { deserializeApiErrorMessage } from '@/services/converters';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useTasks } from '@/store/tasks';
import { type ActionStatus } from '@/store/types';
import { type Writeable } from '@/types';
import {
  type NewTrade,
  type Trade,
  type TradeEntry,
  type TradeType
} from '@/types/history/trades';
import { TaskType } from '@/types/task-type';
import { Zero, bigNumberifyFromRef } from '@/utils/bignumbers';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';
import TwoFieldsAmountInput from '@/components/inputs/TwoFieldsAmountInput.vue';

const props = defineProps({
  value: { required: false, type: Boolean, default: false },
  edit: {
    required: false,
    type: Object as PropType<Trade | null>,
    default: null
  },
  saveData: {
    required: true,
    type: Function as PropType<
      (trade: NewTrade | TradeEntry) => Promise<ActionStatus>
    >
  }
});

const emit = defineEmits<{ (e: 'input', valid: boolean): void }>();

const { t } = useI18n();
const { edit, saveData } = toRefs(props);

const input = (valid: boolean) => emit('input', valid);

const { isTaskRunning } = useTasks();
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
  baseAsset: {
    required: helpers.withMessage(
      t('external_trade_form.validation.non_empty_base').toString(),
      required
    )
  },
  quoteAsset: {
    required: helpers.withMessage(
      t('external_trade_form.validation.non_empty_quote').toString(),
      required
    )
  },
  amount: {
    required: helpers.withMessage(
      t('external_trade_form.validation.non_empty_amount').toString(),
      required
    )
  },
  rate: {
    required: helpers.withMessage(
      t('external_trade_form.validation.non_empty_rate').toString(),
      required
    )
  },
  quoteAmount: {
    required: helpers.withMessage(
      t('external_trade_form.validation.non_empty_quote_amount').toString(),
      required
    )
  },
  fee: {
    required: helpers.withMessage(
      t('external_trade_form.validation.non_empty_fee').toString(),
      requiredIf(refIsTruthy(feeCurrency))
    )
  },
  feeCurrency: {
    required: helpers.withMessage(
      t('external_trade_form.validation.non_empty_fee_currency').toString(),
      requiredIf(refIsTruthy(fee))
    )
  }
};

const v$ = useVuelidate(
  rules,
  {
    baseAsset: base,
    quoteAsset: quote,
    amount,
    rate,
    quoteAmount,
    fee,
    feeCurrency
  },
  {
    $autoDirty: true,
    $externalResults: errorMessages
  }
);

watch(v$, ({ $invalid }) => {
  input(!$invalid);
});

const triggerFeeValidator = () => {
  get(feeInput)?.textInput?.validate(true);
  get(feeCurrencyInput)?.autoCompleteInput?.validate(true);
};

const baseHint = computed<string>(() => {
  return get(type) === 'buy'
    ? t('external_trade_form.buy_base').toString()
    : t('external_trade_form.sell_base').toString();
});

const quoteHint = computed<string>(() => {
  return get(type) === 'buy'
    ? t('external_trade_form.buy_quote').toString()
    : t('external_trade_form.sell_quote').toString();
});

const shouldRenderSummary = computed<boolean>(() => {
  return !!(get(type) && get(base) && get(quote) && get(amount) && get(rate));
});

const fetching = isTaskRunning(TaskType.FETCH_HISTORIC_PRICE);

const numericAmount = bigNumberifyFromRef(amount);
const numericQuoteAmount = bigNumberifyFromRef(quoteAmount);
const numericFee = bigNumberifyFromRef(fee);
const numericRate = bigNumberifyFromRef(rate);

const reset = () => {
  set(id, '');
  set(datetime, convertFromTimestamp(dayjs().unix(), true));
  set(amount, '');
  set(rate, '');
  set(fee, '');
  set(feeCurrency, '');
  set(link, '');
  set(notes, '');
  set(type, 'buy');
  set(errorMessages, {});
};

const setEditMode = () => {
  const trade = get(edit);
  if (!trade) {
    reset();
    return;
  }

  set(base, trade.baseAsset);
  set(quote, trade.quoteAsset);
  set(datetime, convertFromTimestamp(trade.timestamp, true));
  set(amount, trade.amount.toFixed());
  set(rate, trade.rate.toFixed());
  set(fee, trade.fee?.toFixed() ?? '');
  set(feeCurrency, trade.feeCurrency ?? '');
  set(link, trade.link ?? '');
  set(notes, trade.notes ?? '');
  set(type, trade.tradeType);
  set(id, trade.tradeId);
};

const save = async (): Promise<boolean> => {
  const amount = get(numericAmount);
  const fee = get(numericFee);
  const rate = get(numericRate);

  const tradePayload: Writeable<NewTrade> = {
    amount: amount.isNaN() ? Zero : amount,
    fee: fee.isNaN() || fee.isZero() ? undefined : fee,
    feeCurrency: get(feeCurrency) ? get(feeCurrency) : undefined,
    link: get(link) ? get(link) : undefined,
    notes: get(notes) ? get(notes) : undefined,
    baseAsset: get(base),
    quoteAsset: get(quote),
    rate: rate.isNaN() ? Zero : rate,
    location: 'external',
    timestamp: convertToTimestamp(get(datetime)),
    tradeType: get(type)
  };

  const save = get(saveData);
  const result = !get(id)
    ? await save(tradePayload)
    : await save({ ...tradePayload, tradeId: get(id) });

  if (result.success) {
    reset();
    return true;
  }

  if (result.message) {
    set(
      errorMessages,
      convertKeys(deserializeApiErrorMessage(result.message) ?? {}, true, false)
    );

    await get(v$).$validate();
  }

  return false;
};

defineExpose({ save, reset, focus });

const updateRate = (forceUpdate = false) => {
  if (
    get(amount) &&
    get(rate) &&
    (!get(quoteAmountInputFocused) || forceUpdate)
  ) {
    set(
      quoteAmount,
      get(numericAmount).multipliedBy(get(numericRate)).toFixed()
    );
  }
};

const fetchPrice = async () => {
  if ((get(rate) && get(edit)) || !get(datetime) || !get(base) || !get(quote)) {
    return;
  }

  const timestamp = convertToTimestamp(get(datetime));
  const fromAsset = get(base);
  const toAsset = get(quote);

  const rateFromHistoricPrice = await getHistoricPrice({
    timestamp,
    fromAsset,
    toAsset
  });

  if (rateFromHistoricPrice.gt(0)) {
    set(rate, rateFromHistoricPrice.toFixed());
    updateRate(true);
  } else if (!get(rate)) {
    set(errorMessages, {
      rate: [t('external_trade_form.rate_not_found').toString()]
    });
    await get(v$).rate.$validate();
    useTimeoutFn(() => {
      set(errorMessages, {});
    }, 4000);
  }
};

const onQuoteAmountChange = () => {
  if (get(amount) && get(quoteAmount) && get(quoteAmountInputFocused)) {
    set(rate, get(numericQuoteAmount).div(get(numericAmount)).toFixed());
  }
};

watch(edit, () => {
  setEditMode();
});

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

onMounted(() => {
  setEditMode();
});
</script>

<template>
  <v-form :value="value" data-cy="trade-form" class="external-trade-form">
    <v-row>
      <v-col>
        <v-row class="pt-1">
          <v-col cols="12" sm="3">
            <date-time-picker
              v-model="datetime"
              required
              outlined
              seconds
              limit-now
              data-cy="date"
              :label="t('external_trade_form.date.label')"
              persistent-hint
              :hint="t('external_trade_form.date.hint')"
              :error-messages="errorMessages['timestamp']"
            />
            <div data-cy="type">
              <v-radio-group
                v-model="type"
                required
                :label="t('external_trade_form.trade_type.label')"
              >
                <v-radio
                  :label="t('external_trade_form.trade_type.buy')"
                  value="buy"
                />
                <v-radio
                  :label="t('external_trade_form.trade_type.sell')"
                  value="sell"
                />
              </v-radio-group>
            </div>
          </v-col>
          <v-col cols="12" sm="9" class="d-flex flex-column">
            <v-row>
              <v-col cols="12" md="6" class="d-flex flex-row align-center">
                <div class="text--secondary external-trade-form__action-hint">
                  {{ baseHint }}
                </div>
                <asset-select
                  v-model="base"
                  outlined
                  required
                  data-cy="base-asset"
                  :error-messages="v$.baseAsset.$errors.map(e => e.$message)"
                  :hint="t('external_trade_form.base_asset.hint')"
                  :label="t('external_trade_form.base_asset.label')"
                />
              </v-col>
              <v-col cols="12" md="6" class="d-flex flex-row align-center">
                <div class="text--secondary external-trade-form__action-hint">
                  {{ quoteHint }}
                </div>
                <asset-select
                  v-model="quote"
                  required
                  outlined
                  data-cy="quote-asset"
                  :error-messages="v$.quoteAsset.$errors.map(e => e.$message)"
                  :hint="t('external_trade_form.quote_asset.hint')"
                  :label="t('external_trade_form.quote_asset.label')"
                />
              </v-col>
            </v-row>
            <div class="mt-4">
              <amount-input
                v-model="amount"
                required
                outlined
                :error-messages="v$.amount.$errors.map(e => e.$message)"
                data-cy="amount"
                :label="t('common.amount')"
                persistent-hint
                :hint="t('external_trade_form.amount.hint')"
              />

              <two-fields-amount-input
                class="mb-5"
                :primary-value.sync="rate"
                :secondary-value.sync="quoteAmount"
                :loading="fetching"
                :disabled="fetching"
                :primary-attrs="{
                  'data-cy': 'rate',
                  label: t('external_trade_form.rate.label'),
                  errorMessages: v$.rate.$errors.map(e => e.$message)
                }"
                :secondary-attrs="{
                  'data-cy': 'quote-amount',
                  label: t('external_trade_form.quote_amount.label'),
                  errorMessages: v$.quoteAmount.$errors.map(e => e.$message)
                }"
                @update:reversed="quoteAmountInputFocused = $event"
              />

              <div
                v-if="shouldRenderSummary"
                class="text-caption green--text mt-n4 mb-n1"
              >
                <v-icon small class="mr-2 green--text">
                  mdi-comment-quote
                </v-icon>
                <i18n
                  v-if="type === 'buy'"
                  path="external_trade_form.summary.buy"
                >
                  <template #label>
                    <strong>
                      {{ t('external_trade_form.summary.label') }}
                    </strong>
                  </template>
                  <template #amount>
                    <strong>
                      <amount-display :value="numericAmount" :tooltip="false" />
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
                      <amount-display :value="numericRate" :tooltip="false" />
                    </strong>
                  </template>
                </i18n>
                <i18n
                  v-if="type === 'sell'"
                  tag="span"
                  path="external_trade_form.summary.sell"
                >
                  <template #label>
                    <strong>
                      {{ t('external_trade_form.summary.label') }}
                    </strong>
                  </template>
                  <template #amount>
                    <strong>
                      <amount-display :value="numericAmount" :tooltip="false" />
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
                      <amount-display :value="numericRate" :tooltip="false" />
                    </strong>
                  </template>
                </i18n>
              </div>
            </div>
          </v-col>
        </v-row>

        <v-divider class="mb-6 mt-2" />

        <v-row class="mb-2">
          <v-col cols="12" md="6">
            <amount-input
              ref="feeInput"
              v-model="fee"
              class="external-trade-form__fee"
              persistent-hint
              outlined
              data-cy="fee"
              :required="!!feeCurrency"
              :label="t('external_trade_form.fee.label')"
              :hint="t('external_trade_form.fee.hint')"
              :error-messages="v$.fee.$errors.map(e => e.$message)"
              @input="triggerFeeValidator"
            />
          </v-col>
          <v-col cols="12" md="6">
            <asset-select
              ref="feeCurrencyInput"
              v-model="feeCurrency"
              data-cy="fee-currency"
              outlined
              persistent-hint
              :label="t('external_trade_form.fee_currency.label')"
              :hint="t('external_trade_form.fee_currency.hint')"
              :required="!!fee"
              :error-messages="v$.feeCurrency.$errors.map(e => e.$message)"
              @input="triggerFeeValidator"
            />
          </v-col>
        </v-row>
        <v-text-field
          v-model="link"
          data-cy="link"
          outlined
          prepend-inner-icon="mdi-link"
          :label="t('external_trade_form.link.label')"
          persistent-hint
          :hint="t('external_trade_form.link.hint')"
          :error-messages="errorMessages['link']"
        />
        <v-textarea
          v-model="notes"
          prepend-inner-icon="mdi-text-box-outline"
          outlined
          data-cy="notes"
          class="mt-4"
          :label="t('external_trade_form.notes.label')"
          persistent-hint
          :hint="t('external_trade_form.notes.hint')"
          :error-messages="errorMessages['notes']"
        />
      </v-col>
    </v-row>
  </v-form>
</template>

<style scoped lang="scss">
.external-trade-form {
  &__action-hint {
    width: 60px;
    margin-top: -2rem;
  }
}
</style>
