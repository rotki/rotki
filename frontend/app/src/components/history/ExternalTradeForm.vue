<template>
  <v-form
    :value="value"
    data-cy="trade-form"
    class="external-trade-form"
    @input="input"
  >
    <v-row>
      <v-col>
        <v-row>
          <v-col cols="12" sm="3">
            <date-time-picker
              v-model="datetime"
              required
              outlined
              class="pt-1"
              seconds
              limit-now
              data-cy="date"
              :label="$t('external_trade_form.date.label')"
              persistent-hint
              :hint="$t('external_trade_form.date.hint')"
              :error-messages="errorMessages['timestamp']"
              @focus="delete errorMessages['timestamp']"
            />
            <div data-cy="type">
              <v-radio-group
                v-model="type"
                required
                :label="$t('external_trade_form.trade_type.label')"
              >
                <v-radio
                  :label="$t('external_trade_form.trade_type.buy')"
                  value="buy"
                />
                <v-radio
                  :label="$t('external_trade_form.trade_type.sell')"
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
                  :rules="baseRules"
                  :hint="$t('external_trade_form.base_asset.hint')"
                  :label="$t('external_trade_form.base_asset.label')"
                  :error-messages="errorMessages['baseAsset']"
                  @focus="delete errorMessages['baseAsset']"
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
                  :rules="quoteRules"
                  :hint="$t('external_trade_form.quote_asset.hint')"
                  :label="$t('external_trade_form.quote_asset.label')"
                  :error-messages="errorMessages['quoteAsset']"
                  @focus="delete errorMessages['quoteAsset']"
                />
              </v-col>
            </v-row>
            <amount-input
              v-model="amount"
              required
              outlined
              :rules="amountRules"
              data-cy="amount"
              :label="$t('external_trade_form.amount.label')"
              persistent-hint
              :hint="$t('external_trade_form.amount.hint')"
              :error-messages="errorMessages['amount']"
              @focus="delete errorMessages['amount']"
            />
            <div
              :class="`external-trade-form__grouped-amount-input d-flex ${
                selectedCalculationInput === 'quoteAmount'
                  ? 'flex-column-reverse'
                  : 'flex-column'
              }`"
            >
              <amount-input
                ref="rateInput"
                v-model="rate"
                :disabled="selectedCalculationInput !== 'rate'"
                :label="$t('external_trade_form.rate.label')"
                :loading="fetching"
                :rules="rateRules"
                data-cy="rate"
                :hide-details="selectedCalculationInput !== 'rate'"
                :class="`${
                  selectedCalculationInput === 'rate'
                    ? 'v-input--is-enabled'
                    : ''
                }`"
                filled
                persistent-hint
                :error-messages="errorMessages['rate']"
                @focus="delete errorMessages['rate']"
              />
              <amount-input
                ref="quoteAmountInput"
                v-model="quoteAmount"
                :disabled="selectedCalculationInput !== 'quoteAmount'"
                :rules="quoteAmountRules"
                data-cy="quote-amount"
                :hide-details="selectedCalculationInput !== 'quoteAmount'"
                :class="`${
                  selectedCalculationInput === 'quoteAmount'
                    ? 'v-input--is-enabled'
                    : ''
                }`"
                :label="$t('external_trade_form.quote_amount.label')"
                filled
                :error-messages="errorMessages['quote_amount']"
                @focus="delete errorMessages['quote_amount']"
              />
              <v-btn
                class="external-trade-form__grouped-amount-input__swap-button"
                fab
                small
                dark
                color="primary"
                data-cy="grouped-amount-input__swap-button"
                @click="swapAmountInput"
              >
                <v-icon>mdi-swap-vertical</v-icon>
              </v-btn>
            </div>
            <div
              v-if="shouldRenderSummary"
              class="text-caption green--text mt-n5"
            >
              <v-icon small class="mr-2 green--text">
                mdi-comment-quote
              </v-icon>
              <i18n
                v-if="type === 'buy'"
                tag="span"
                path="external_trade_form.summary.buy"
              >
                <template #label>
                  <strong>{{ $t('external_trade_form.summary.label') }}</strong>
                </template>
                <template #amount>
                  <strong>
                    <amount-display :value="numericAmount" :tooltip="false" />
                  </strong>
                </template>
                <template #base>
                  <strong>{{ getAssetSymbol(base) }}</strong>
                </template>
                <template #quote>
                  <strong>{{ getAssetSymbol(quote) }}</strong>
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
                  <strong>{{ $t('external_trade_form.summary.label') }}</strong>
                </template>
                <template #amount>
                  <strong>
                    <amount-display :value="numericAmount" :tooltip="false" />
                  </strong>
                </template>
                <template #base>
                  <strong>{{ getAssetSymbol(base) }}</strong>
                </template>
                <template #quote>
                  <strong>{{ getAssetSymbol(quote) }}</strong>
                </template>
                <template #rate>
                  <strong>
                    <amount-display :value="numericRate" :tooltip="false" />
                  </strong>
                </template>
              </i18n>
            </div>
          </v-col>
        </v-row>

        <v-divider class="mb-6 mt-2" />

        <v-row>
          <v-col cols="12" md="6">
            <amount-input
              v-model="fee"
              class="external-trade-form__fee"
              outlined
              data-cy="fee"
              :label="$t('external_trade_form.fee.label')"
              persistent-hint
              :hint="$t('external_trade_form.fee.hint')"
              :error-messages="errorMessages['fee']"
              @focus="delete errorMessages['fee']"
            />
          </v-col>
          <v-col cols="12" md="6">
            <asset-select
              v-model="feeCurrency"
              outlined
              persistent-hint
              :label="$t('external_trade_form.fee_currency.label')"
              :hint="$t('external_trade_form.fee_currency.hint')"
              data-cy="fee-currency"
              :error-messages="errorMessages['feeCurrency']"
              @focus="delete errorMessages['feeCurrency']"
            />
          </v-col>
        </v-row>
        <v-text-field
          v-model="link"
          data-cy="link"
          outlined
          prepend-inner-icon="mdi-link"
          :label="$t('external_trade_form.link.label')"
          persistent-hint
          :hint="$t('external_trade_form.link.hint')"
          :error-messages="errorMessages['link']"
          @focus="delete errorMessages['link']"
        />
        <v-textarea
          v-model="notes"
          prepend-inner-icon="mdi-text-box-outline"
          outlined
          data-cy="notes"
          class="mt-4"
          :label="$t('external_trade_form.notes.label')"
          persistent-hint
          :hint="$t('external_trade_form.notes.hint')"
          :error-messages="errorMessages['notes']"
          @focus="delete errorMessages['notes']"
        />
      </v-col>
    </v-row>
  </v-form>
</template>

<script lang="ts">
import { BigNumber } from '@rotki/common';
import {
  computed,
  defineComponent,
  nextTick,
  onMounted,
  PropType,
  ref,
  toRefs,
  unref,
  watch
} from '@vue/composition-api';
import dayjs from 'dayjs';
import { setupGeneralBalances } from '@/composables/balances';
import i18n from '@/i18n';
import { convertKeys } from '@/services/axios-tranformers';
import { deserializeApiErrorMessage } from '@/services/converters';
import { NewTrade, Trade, TradeType } from '@/services/history/types';
import { useAssetInfoRetrieval } from '@/store/assets';
import { TradeEntry } from '@/store/history/types';
import { useTasks } from '@/store/tasks';
import { ActionStatus } from '@/store/types';
import { Writeable } from '@/types';
import { TaskType } from '@/types/task-type';
import { bigNumberifyFromRef, Zero } from '@/utils/bignumbers';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';

const ExternalTradeForm = defineComponent({
  name: 'ExternalTradeForm',
  props: {
    value: { required: false, type: Boolean, default: false },
    edit: { required: false, type: Object as PropType<Trade>, default: null },
    saveData: {
      required: true,
      type: Function as PropType<
        (trade: NewTrade | TradeEntry) => Promise<ActionStatus>
      >
    }
  },
  emits: ['input'],
  setup(props, { emit }) {
    const { edit } = toRefs(props);
    const { saveData } = props;

    const { getAssetSymbol } = useAssetInfoRetrieval();
    const input = (valid: boolean) => emit('input', valid);

    const { isTaskRunning } = useTasks();
    const { fetchHistoricPrice } = setupGeneralBalances();

    const id = ref<string>('');
    const base = ref<string>('');
    const quote = ref<string>('');
    const datetime = ref<string>('');
    const amount = ref<string>('');
    const rate = ref<string>('');
    const quoteAmount = ref<string>('');
    const selectedCalculationInput = ref<'rate' | 'quoteAmount'>('rate');
    const fee = ref<string>('');
    const feeCurrency = ref<string>('');
    const link = ref<string>('');
    const notes = ref<string>('');
    const type = ref<TradeType>('buy');

    const errorMessages = ref<{ [field: string]: string[] }>({});

    const quoteAmountInput = ref<any>(null);
    const rateInput = ref<any>(null);

    const baseRules = [
      (v: string) =>
        !!v || i18n.t('external_trade_form.validation.non_empty_base')
    ];
    const quoteRules = [
      (v: string) =>
        !!v || i18n.t('external_trade_form.validation.non_empty_quote')
    ];
    const amountRules = [
      (v: string) =>
        !!v || i18n.t('external_trade_form.validation.non_empty_amount')
    ];
    const rateRules = [
      (v: string) =>
        !!v || i18n.t('external_trade_form.validation.non_empty_rate')
    ];
    const quoteAmountRules = [
      (v: string) =>
        !!v || i18n.t('external_trade_form.validation.non_empty_quote_amount')
    ];

    const baseHint = computed<string>(() => {
      return unref(type) === 'buy'
        ? i18n.t('external_trade_form.buy_base').toString()
        : i18n.t('external_trade_form.sell_base').toString();
    });

    const quoteHint = computed<string>(() => {
      return unref(type) === 'buy'
        ? i18n.t('external_trade_form.buy_quote').toString()
        : i18n.t('external_trade_form.sell_quote').toString();
    });

    const shouldRenderSummary = computed<boolean>(() => {
      return !!(
        unref(type) &&
        unref(base) &&
        unref(quote) &&
        unref(amount) &&
        unref(rate)
      );
    });

    const fetching = computed<boolean>(() => {
      return isTaskRunning(TaskType.FETCH_HISTORIC_PRICE).value;
    });

    const numericAmount = bigNumberifyFromRef(amount);
    const numericFee = bigNumberifyFromRef(fee);
    const numericRate = bigNumberifyFromRef(rate);

    const reset = () => {
      id.value = '';
      datetime.value = convertFromTimestamp(dayjs().unix(), true);
      amount.value = '';
      rate.value = '';
      fee.value = '';
      feeCurrency.value = '';
      link.value = '';
      notes.value = '';
      type.value = 'buy';
      errorMessages.value = {};
    };

    const setEditMode = () => {
      if (!unref(edit)) {
        reset();
        return;
      }

      const trade: Trade = unref(edit);

      base.value = trade.baseAsset;
      quote.value = trade.quoteAsset;
      datetime.value = convertFromTimestamp(trade.timestamp, true);
      amount.value = trade.amount.toString();
      rate.value = trade.rate.toString();
      fee.value = trade.fee?.toString() ?? '';
      feeCurrency.value = trade.feeCurrency ? trade.feeCurrency : '';
      link.value = trade.link ?? '';
      notes.value = trade.notes ?? '';
      type.value = trade.tradeType;
      id.value = trade.tradeId;
    };

    const save = async (): Promise<boolean> => {
      const amount = unref(numericAmount);
      const fee = unref(numericFee);
      const rate = unref(numericRate);

      const tradePayload: Writeable<NewTrade> = {
        amount: amount.isNaN() ? Zero : amount,
        fee: fee.isNaN() ? undefined : fee,
        feeCurrency: unref(feeCurrency) ? unref(feeCurrency) : undefined,
        link: unref(link) ? unref(link) : undefined,
        notes: unref(notes) ? unref(notes) : undefined,
        baseAsset: unref(base),
        quoteAsset: unref(quote),
        rate: rate.isNaN() ? Zero : rate,
        location: 'external',
        timestamp: convertToTimestamp(unref(datetime)),
        tradeType: unref(type)
      };

      const result = !unref(id)
        ? await saveData(tradePayload)
        : await saveData({ ...tradePayload, tradeId: unref(id) });

      if (result.success) {
        reset();
        return true;
      }

      if (result.message) {
        errorMessages.value = convertKeys(
          deserializeApiErrorMessage(result.message) ?? {},
          true,
          false
        );
      }

      return false;
    };

    const swapAmountInput = () => {
      if (unref(selectedCalculationInput) === 'rate') {
        selectedCalculationInput.value = 'quoteAmount';
        nextTick(() => {
          quoteAmountInput.value?.focus();
        });
      } else {
        selectedCalculationInput.value = 'rate';
        nextTick(() => {
          rateInput.value?.focus();
        });
      }
    };

    const updateRate = (forceUpdate: boolean = false) => {
      if (
        unref(amount) &&
        unref(rate) &&
        (unref(selectedCalculationInput) === 'rate' || forceUpdate)
      ) {
        quoteAmount.value = new BigNumber(unref(amount))
          .multipliedBy(new BigNumber(unref(rate)))
          .toString();
      }
    };

    const fetchPrice = async () => {
      if (
        (unref(rate) && unref(edit)) ||
        !unref(datetime) ||
        !unref(base) ||
        !unref(quote)
      ) {
        return;
      }

      const timestamp = convertToTimestamp(unref(datetime));
      const fromAsset = unref(base);
      const toAsset = unref(quote);

      const rateFromHistoricPrice = await fetchHistoricPrice({
        timestamp,
        fromAsset,
        toAsset
      });
      if (rateFromHistoricPrice.gt(0)) {
        rate.value = rateFromHistoricPrice.toString();
        updateRate(true);
      } else if (!unref(rate)) {
        errorMessages.value = {
          rate: [i18n.t('external_trade_form.rate_not_found').toString()]
        };
        setTimeout(() => {
          errorMessages.value = {};
        }, 4000);
      }
    };

    const onQuoteAmountChange = () => {
      if (
        unref(amount) &&
        unref(quoteAmount) &&
        unref(selectedCalculationInput) === 'quoteAmount'
      ) {
        rate.value = new BigNumber(unref(quoteAmount))
          .div(new BigNumber(unref(amount)))
          .toString();
      }
    };

    watch(edit, () => {
      setEditMode();
    });

    watch([datetime, quote, base], () => {
      fetchPrice();
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

    return {
      getAssetSymbol,
      input,
      id,
      base,
      quote,
      datetime,
      amount,
      rate,
      quoteAmount,
      selectedCalculationInput,
      fee,
      feeCurrency,
      link,
      notes,
      type,
      rateInput,
      quoteAmountInput,
      errorMessages,
      baseRules,
      quoteRules,
      amountRules,
      rateRules,
      quoteAmountRules,
      baseHint,
      quoteHint,
      shouldRenderSummary,
      fetching,
      numericAmount,
      numericRate,
      numericFee,
      swapAmountInput,
      save,
      reset
    };
  }
});

export type ExternalTradeFormInstance = InstanceType<typeof ExternalTradeForm>;

export default ExternalTradeForm;
</script>

<style scoped lang="scss">
/* stylelint-disable */
.external-trade-form {
  &__action-hint {
    width: 60px;
    margin-top: -24px;
  }

  &__grouped-amount-input {
    position: relative;
    margin-bottom: 30px;

    ::v-deep {
      .v-input {
        position: static;

        &__slot {
          margin-bottom: 0;
          background: transparent !important;
        }

        &--is-disabled {
          .v-input__control {
            .v-input__slot {
              &::before {
                content: none;
              }
            }
          }
        }

        .v-text-field__details {
          position: absolute;
          bottom: -30px;
          width: 100%;
        }

        &--is-enabled {
          &::before {
            content: '';
            width: 100%;
            height: 100%;
            position: absolute;
            top: 0;
            left: 0;
            border: 1px solid rgba(0, 0, 0, 0.42);
            border-radius: 4px;
          }

          &.v-input--is-focused {
            &::before {
              border: 2px solid var(--v-primary-base) !important;
            }
          }

          &.error--text {
            &::before {
              border: 2px solid var(--v-error-base) !important;
            }
          }
        }
      }
    }

    &__swap-button {
      position: absolute;
      right: 20px;
      top: 50%;
      transform: translateY(-50%);
    }
  }

  ::v-deep {
    .v-select.v-text-field--outlined:not(.v-text-field--single-line) {
      .v-select__selections {
        padding: 0 !important;
      }
    }
  }

  &__fee {
    height: 60px;
  }
}

.theme {
  &--dark {
    .external-trade-form {
      &__grouped-amount-input {
        ::v-deep {
          .v-input {
            &__slot {
              &::before {
                border-color: hsla(0, 0%, 100%, 0.24) !important;
              }
            }

            &--is-enabled {
              &::before {
                border-color: hsla(0, 0%, 100%, 0.24);
              }
            }
          }
        }
      }
    }
  }
}
/* stylelint-enable */
</style>
