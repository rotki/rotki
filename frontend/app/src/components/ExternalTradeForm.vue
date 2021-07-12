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
                  data-cy="base_asset"
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
                  data-cy="quote_asset"
                  :rules="quoteRules"
                  :hint="$t('external_trade_form.quote_asset.hint')"
                  :label="$t('external_trade_form.quote_asset.label')"
                  :error-messages="errorMessages['quoteAsset']"
                  @focus="delete errorMessages['quoteAsset']"
                />
              </v-col>
            </v-row>
            <v-text-field
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
            <v-text-field
              v-model="rate"
              :rules="rateRules"
              outlined
              data-cy="rate"
              :loading="fetching"
              :label="$t('external_trade_form.rate.label')"
              persistent-hint
              :hint="$t('external_trade_form.rate.hint')"
              :error-messages="errorMessages['rate']"
              @focus="delete errorMessages['rate']"
            />
          </v-col>
        </v-row>

        <v-divider class="mb-6 mt-2" />

        <v-row>
          <v-col cols="12" md="6">
            <v-text-field
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
import { default as BigNumber } from 'bignumber.js';
import dayjs from 'dayjs';
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import { mapActions, mapGetters } from 'vuex';
import DateTimePicker from '@/components/dialogs/DateTimePicker.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import { TaskType } from '@/model/task-type';
import { convertKeys } from '@/services/axios-tranformers';
import { deserializeApiErrorMessage } from '@/services/converters';
import { NewTrade, Trade, TradeType } from '@/services/history/types';
import { HistoricPricePayload } from '@/store/balances/types';
import { HistoryActions } from '@/store/history/consts';
import { ActionStatus } from '@/store/types';
import { Writeable } from '@/types';
import { assert } from '@/utils/assertions';
import { bigNumberify, Zero } from '@/utils/bignumbers';

@Component({
  components: { AssetSelect, DateTimePicker },
  computed: {
    ...mapGetters('tasks', ['isTaskRunning'])
  },
  methods: {
    ...mapActions('history', [
      HistoryActions.ADD_EXTERNAL_TRADE,
      HistoryActions.EDIT_EXTERNAL_TRADE
    ]),
    ...mapActions('balances', ['fetchHistoricPrice'])
  }
})
export default class ExternalTradeForm extends Vue {
  @Prop({ required: false, type: Boolean, default: false })
  value!: boolean;

  @Prop({ required: false, default: null })
  edit!: Trade | null;

  @Emit()
  input(_valid: boolean) {}

  errorMessages: {
    [field: string]: string[];
  } = {};
  addExternalTrade!: (trade: NewTrade) => Promise<ActionStatus>;
  editExternalTrade!: (
    trade: Omit<Trade, 'ignoredInAccounting'>
  ) => Promise<ActionStatus>;
  isTaskRunning!: (type: TaskType) => boolean;
  fetchHistoricPrice!: (payload: HistoricPricePayload) => Promise<BigNumber>;

  private static format = 'DD/MM/YYYY HH:mm:ss';
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

  rateMessages: string[] = [];

  id: string = '';
  datetime: string = '';
  amount: string = '';
  rate: string = '';
  fee: string = '';
  feeCurrency: string = '';
  link: string = '';
  notes: string = '';
  type: TradeType = 'buy';

  get fetching(): boolean {
    return this.isTaskRunning(TaskType.FETCH_HISTORIC_PRICE);
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

  async fetchPrice() {
    if (
      (this.rate && this.edit) ||
      !this.datetime ||
      !this.base ||
      !this.quote
    ) {
      return;
    }

    const timestamp = dayjs(this.datetime, ExternalTradeForm.format).unix();
    const fromAsset = this.base;
    const toAsset = this.quote;

    const rate = await this.fetchHistoricPrice({
      timestamp,
      fromAsset,
      toAsset
    });
    if (rate.gt(0)) {
      this.rate = rate.toString();
    } else {
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
    assert(typeof trade.baseAsset === 'string');
    assert(typeof trade.quoteAsset === 'string');

    this.base = trade.baseAsset;
    this.quote = trade.quoteAsset;
    this.datetime = dayjs(trade.timestamp * 1000).format(
      ExternalTradeForm.format
    );
    this.amount = trade.amount.toString();
    this.rate = trade.rate.toString();
    this.fee = trade.fee?.toString() ?? '';
    this.feeCurrency =
      trade.feeCurrency && typeof trade.feeCurrency === 'string'
        ? trade.feeCurrency
        : '';
    this.link = trade.link ?? '';
    this.notes = trade.notes ?? '';
    this.type = trade.tradeType;
    this.id = trade.tradeId;
  }

  reset() {
    this.id = '';
    this.datetime = dayjs().format(ExternalTradeForm.format);
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
      timestamp: dayjs(this.datetime, ExternalTradeForm.format).unix(),
      tradeType: this.type
    };

    const { success, message } = !this.id
      ? await this.addExternalTrade(tradePayload)
      : await this.editExternalTrade({ ...tradePayload, tradeId: this.id });

    if (success) {
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
}
</script>

<style scoped lang="scss">
.external-trade-form {
  &__action-hint {
    width: 60px;
    margin-top: -24px;
  }

  ::v-deep {
    /* stylelint-disable selector-class-pattern,selector-nested-pattern,scss/selector-nest-combinators,rule-empty-line-before */
    .v-select.v-text-field--outlined:not(.v-text-field--single-line) {
      .v-select__selections {
        padding: 0 !important;
      }
    }

    /* stylelint-enable selector-class-pattern,selector-nested-pattern,scss/selector-nest-combinators,rule-empty-line-before */
  }

  &__fee {
    height: 60px;
  }
}
</style>
