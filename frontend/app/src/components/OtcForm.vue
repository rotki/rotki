<template>
  <div class="otc-form">
    <v-row>
      <v-col>
        <v-row>
          <v-col cols="12" sm="3">
            <date-time-picker
              v-model="datetime"
              class="otc-form__date"
              :label="$t('otc_form.date.label')"
              persistent-hint
              :hint="$t('otc_form.date.hint')"
              :error-messages="errorMessages['timestamp']"
            />
            <v-radio-group
              v-model="type"
              :label="$t('otc_form.trade_type.label')"
              class="otc-form__type"
            >
              <v-radio :label="$t('otc_form.trade_type.buy')" value="buy" />
              <v-radio :label="$t('otc_form.trade_type.sell')" value="sell" />
            </v-radio-group>
          </v-col>
          <v-col cols="12" sm="9" class="d-flex flex-column">
            <v-text-field
              v-model="pair"
              class="otc-form__pair"
              :label="$t('otc_form.pair.label')"
              persistent-hint
              :hint="$t('otc_form.pair.hint')"
              :error-messages="errorMessages['pair']"
            />
            <v-text-field
              v-model="amount"
              class="otc-form__amount"
              :label="$t('otc_form.amount.label')"
              persistent-hint
              :hint="$t('otc_form.amount.hint')"
              :error-messages="errorMessages['amount']"
            />
            <v-text-field
              v-model="rate"
              class="otc-form__rate"
              :label="$t('otc_form.rate.label')"
              persistent-hint
              :hint="$t('otc_form.rate.hint')"
              :error-messages="errorMessages['rate']"
            />
            <v-text-field
              v-model="fee"
              class="otc-form__fee"
              :label="$t('otc_form.fee.label')"
              persistent-hint
              :hint="$t('otc_form.fee.hint')"
              :error-messages="errorMessages['fee']"
            />
            <asset-select
              v-model="feeCurrency"
              :label="$t('otc_form.fee_currency.label')"
              class="otc-form__fee-currency"
              :rules="assetRules"
              :error-messages="errorMessages['feeCurrency']"
            />
          </v-col>
        </v-row>
        <v-text-field
          v-model="link"
          class="otc-form__link"
          :label="$t('otc_form.link.label')"
          persistent-hint
          :hint="$t('otc_form.link.hint')"
          :error-messages="errorMessages['link']"
        />
        <v-textarea
          v-model="notes"
          class="otc-form__notes"
          :label="$t('otc_form.notes.label')"
          persistent-hint
          :hint="$t('otc_form.notes.hint')"
          :error-messages="errorMessages['notes']"
        />
      </v-col>
    </v-row>
  </div>
</template>

<script lang="ts">
import moment from 'moment';
import { Component, Prop, Vue, Watch } from 'vue-property-decorator';
import { mapActions } from 'vuex';
import DateTimePicker from '@/components/dialogs/DateTimePicker.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import { convertKeys } from '@/services/axios-tranformers';
import { deserializeApiErrorMessage } from '@/services/converters';
import { Trade, TradeType, NewTrade } from '@/services/history/types';
import { ActionStatus } from '@/store/types';
import { Writeable } from '@/types';
import { bigNumberify, Zero } from '@/utils/bignumbers';

@Component({
  components: { AssetSelect, DateTimePicker },
  methods: {
    ...mapActions('history', ['addExternalTrade', 'editExternalTrade'])
  }
})
export default class OtcForm extends Vue {
  @Prop({ required: false, default: null })
  edit!: Trade | null;
  errorMessages: {
    [field: string]: string[];
  } = {};
  addExternalTrade!: (trade: NewTrade) => Promise<ActionStatus>;
  editExternalTrade!: (
    trade: Omit<Trade, 'ignoredInAccounting'>
  ) => Promise<ActionStatus>;

  private static format = 'DD/MM/YYYY HH:mm';
  readonly assetRules = [
    (v: string) => !!v || this.$t('otc_form.validation.non_empty_fee')
  ];

  id: string = '';
  pair: string = '';
  datetime: string = '';
  amount: string = '';
  rate: string = '';
  fee: string = '';
  feeCurrency: string = '';
  link: string = '';
  notes: string = '';
  type: TradeType = 'buy';

  mounted() {
    this.setEditMode();
  }

  @Watch('edit')
  onEdit() {
    this.setEditMode();
  }

  private setEditMode() {
    if (!this.edit) {
      this.reset();
      return;
    }

    const trade: Trade = this.edit;
    this.pair = trade.pair;
    this.datetime = moment(trade.timestamp * 1000).format(OtcForm.format);
    this.amount = trade.amount.toString();
    this.rate = trade.rate.toString();
    this.fee = trade.fee.toString();
    this.feeCurrency = trade.feeCurrency;
    this.link = trade.link;
    this.notes = trade.notes;
    this.type = trade.tradeType;
    this.id = trade.tradeId;
  }

  reset() {
    this.id = '';
    this.pair = '';
    this.datetime = moment().format(OtcForm.format);
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
      fee: fee.isNaN() ? Zero : fee,
      feeCurrency: this.feeCurrency,
      link: this.link,
      notes: this.notes,
      pair: this.pair,
      rate: rate.isNaN() ? Zero : rate,
      location: 'external',
      timestamp: moment(this.datetime, OtcForm.format).unix(),
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
        true
      );
    }

    return false;
  }
}
</script>
