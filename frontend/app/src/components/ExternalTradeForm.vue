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
                  <strong>{{ amount }}</strong>
                </template>
                <template #base>
                  <strong>{{ getSymbol(base) }}</strong>
                </template>
                <template #quote>
                  <strong>{{ getSymbol(quote) }}</strong>
                </template>
                <template #rate>
                  <strong>{{ rate }}</strong>
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
                  <strong>{{ amount }}</strong>
                </template>
                <template #base>
                  <strong>{{ getSymbol(base) }}</strong>
                </template>
                <template #quote>
                  <strong>{{ getSymbol(quote) }}</strong>
                </template>
                <template #rate>
                  <strong>{{ rate }}</strong>
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
import { SupportedAsset } from '@rotki/common/lib/data';
import { Ref } from '@vue/composition-api';
import dayjs from 'dayjs';
import { mapState as mapPiniaState } from 'pinia';
import { Component, Emit, Mixins, Prop, Watch } from 'vue-property-decorator';
import { mapActions, mapState } from 'vuex';
import DateTimePicker from '@/components/dialogs/DateTimePicker.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import AssetMixin from '@/mixins/asset-mixin';
import { convertKeys } from '@/services/axios-tranformers';
import { deserializeApiErrorMessage } from '@/services/converters';
import { NewTrade, Trade, TradeType } from '@/services/history/types';
import { HistoricPricePayload } from '@/store/balances/types';
import { HistoryActions } from '@/store/history/consts';
import { useTasks } from '@/store/tasks';
import { ActionStatus } from '@/store/types';
import { Writeable } from '@/types';
import { TaskType } from '@/types/task-type';
import { bigNumberify, Zero } from '@/utils/bignumbers';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';

@Component({
  components: { AssetSelect, DateTimePicker },
  computed: {
    ...mapPiniaState(useTasks, ['isTaskRunning']),
    ...mapState('balances', ['supportedAssets'])
  },
  methods: {
    ...mapActions('history', [
      HistoryActions.ADD_EXTERNAL_TRADE,
      HistoryActions.EDIT_EXTERNAL_TRADE
    ]),
    ...mapActions('balances', ['fetchHistoricPrice'])
  }
})
export default class ExternalTradeForm extends Mixins(AssetMixin) {
  @Prop({ required: false, type: Boolean, default: false })
  value!: boolean;

  @Prop({ required: false, default: null })
  edit!: Trade | null;

  supportedAssets!: SupportedAsset[];

  @Emit()
  input(_valid: boolean) {}

  @Emit()
  refresh() {}

  errorMessages: {
    [field: string]: string[];
  } = {};
  addExternalTrade!: (trade: NewTrade) => Promise<ActionStatus>;
  editExternalTrade!: (
    trade: Omit<Trade, 'ignoredInAccounting'>
  ) => Promise<ActionStatus>;
  isTaskRunning!: (type: TaskType) => Ref<boolean>;
  fetchHistoricPrice!: (payload: HistoricPricePayload) => Promise<BigNumber>;

  readonly baseRules = [
    (v: string) =>
      !!v || this.$t('external_trade_form.validation.non_empty_base')
  ];
  readonly quoteRules = [
    (v: string) =>
      !!v || this.$t('external_trade_form.validation.non_empty_quote')
  ];
  readonly amountRules = [
    (v: string) =>
      !!v || this.$t('external_trade_form.validation.non_empty_amount')
  ];
  readonly rateRules = [
    (v: string) =>
      !!v || this.$t('external_trade_form.validation.non_empty_rate')
  ];
  readonly quoteAmountRules = [
    (v: string) =>
      !!v || this.$t('external_trade_form.validation.non_empty_quote_amount')
  ];

  base: string = '';
  quote: string = '';

  get baseHint(): string {
    return this.type === 'buy'
      ? this.$t('external_trade_form.buy_base').toString()
      : this.$t('external_trade_form.sell_base').toString();
  }

  get quoteHint(): string {
    return this.type === 'buy'
      ? this.$t('external_trade_form.buy_quote').toString()
      : this.$t('external_trade_form.sell_quote').toString();
  }

  get shouldRenderSummary(): boolean {
    return !!(this.type && this.base && this.quote && this.amount && this.rate);
  }

  rateMessages: string[] = [];

  id: string = '';
  datetime: string = '';
  amount: string = '';
  rate: string = '';
  quoteAmount: string = '';
  selectedCalculationInput: 'rate' | 'quoteAmount' = 'rate';
  fee: string = '';
  feeCurrency: string = '';
  link: string = '';
  notes: string = '';
  type: TradeType = 'buy';

  get fetching(): boolean {
    return this.isTaskRunning(TaskType.FETCH_HISTORIC_PRICE).value;
  }

  mounted() {
    this.setEditMode();
  }

  @Watch('edit')
  onEdit() {
    this.setEditMode();
  }

  @Watch('datetime')
  async onDateChange() {
    await this.fetchPrice();
  }

  @Watch('quote')
  async onQuoteChange() {
    await this.fetchPrice();
  }

  @Watch('base')
  async onBaseChange() {
    await this.fetchPrice();
  }

  @Watch('amount')
  async onAmountChange() {
    this.onRateChange();
    this.onQuoteAmountChange();
  }

  @Watch('rate')
  onRateChange() {
    this.updateRate();
  }

  updateRate(forceUpdate: boolean = false) {
    if (
      this.amount &&
      this.rate &&
      (this.selectedCalculationInput === 'rate' || forceUpdate)
    ) {
      this.quoteAmount = new BigNumber(this.amount)
        .multipliedBy(new BigNumber(this.rate))
        .toString();
    }
  }

  @Watch('quoteAmount')
  onQuoteAmountChange() {
    if (
      this.amount &&
      this.quoteAmount &&
      this.selectedCalculationInput === 'quoteAmount'
    ) {
      this.rate = new BigNumber(this.quoteAmount)
        .div(new BigNumber(this.amount))
        .toString();
    }
  }

  async fetchPrice() {
    if (
      (this.rate && this.edit) ||
      !this.datetime ||
      !this.base ||
      !this.quote
    ) {
      return;
    }

    const timestamp = convertToTimestamp(this.datetime);
    const fromAsset = this.base;
    const toAsset = this.quote;

    const rate = await this.fetchHistoricPrice({
      timestamp,
      fromAsset,
      toAsset
    });
    if (rate.gt(0)) {
      this.rate = rate.toString();
      this.updateRate(true);
    } else if (!this.rate) {
      this.errorMessages = {
        rate: [this.$t('external_trade_form.rate_not_found').toString()]
      };
      setTimeout(() => {
        this.errorMessages = {};
      }, 4000);
    }
  }

  private setEditMode() {
    if (!this.edit) {
      this.reset();
      return;
    }

    const trade: Trade = this.edit;

    this.base = trade.baseAsset;
    this.quote = trade.quoteAsset;
    this.datetime = convertFromTimestamp(trade.timestamp, true);
    this.amount = trade.amount.toString();
    this.rate = trade.rate.toString();
    this.fee = trade.fee?.toString() ?? '';
    this.feeCurrency = trade.feeCurrency ? trade.feeCurrency : '';
    this.link = trade.link ?? '';
    this.notes = trade.notes ?? '';
    this.type = trade.tradeType;
    this.id = trade.tradeId;
  }

  reset() {
    this.id = '';
    this.datetime = convertFromTimestamp(dayjs().unix(), true);
    this.amount = '';
    this.rate = '';
    this.fee = '';
    this.feeCurrency = '';
    this.link = '';
    this.notes = '';
    this.type = 'buy';
    this.errorMessages = {};
  }

  async save(): Promise<boolean> {
    const amount = bigNumberify(this.amount);
    const fee = bigNumberify(this.fee);
    const rate = bigNumberify(this.rate);

    const tradePayload: Writeable<NewTrade> = {
      amount: amount.isNaN() ? Zero : amount,
      fee: fee.isNaN() ? undefined : fee,
      feeCurrency: this.feeCurrency ? this.feeCurrency : undefined,
      link: this.link ? this.link : undefined,
      notes: this.notes ? this.notes : undefined,
      baseAsset: this.base,
      quoteAsset: this.quote,
      rate: rate.isNaN() ? Zero : rate,
      location: 'external',
      timestamp: convertToTimestamp(this.datetime),
      tradeType: this.type
    };

    const { success, message } = !this.id
      ? await this.addExternalTrade(tradePayload)
      : await this.editExternalTrade({ ...tradePayload, tradeId: this.id });

    if (success) {
      this.refresh();
      this.reset();
      return true;
    }
    if (message) {
      this.errorMessages = convertKeys(
        deserializeApiErrorMessage(message) ?? {},
        true,
        false
      );
    }

    return false;
  }

  swapAmountInput() {
    if (this.selectedCalculationInput === 'rate') {
      this.selectedCalculationInput = 'quoteAmount';
      this.$nextTick(() => {
        const quoteAmountInput = this.$refs.quoteAmountInput as any;
        if (quoteAmountInput) {
          quoteAmountInput.focus();
        }
      });
    } else {
      this.selectedCalculationInput = 'rate';
      this.$nextTick(() => {
        const rateInput = this.$refs.rateInput as any;
        if (rateInput) {
          rateInput.focus();
        }
      });
    }
  }
}
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
