<template>
  <div class="otc-form">
    <v-row>
      <v-col>
        <v-row>
          <v-col cols="12" sm="3">
            <date-time-picker
              v-model="datetime"
              class="otc-form__date"
              label="Time"
              persistent-hint
              hint="Time the trade took place"
              :error-messages="errorMessages['timestamp']"
            ></date-time-picker>
            <v-radio-group
              v-model="type"
              label="Trade type"
              class="otc-form__type"
            >
              <v-radio label="Buy" value="buy"></v-radio>
              <v-radio label="Sell" value="sell"></v-radio>
            </v-radio-group>
          </v-col>
          <v-col cols="12" sm="9" class="d-flex flex-column">
            <v-text-field
              v-model="pair"
              class="otc-form__pair"
              label="Pair"
              persistent-hint
              hint="Pair for the trade. BASECURRENCY_QUOTECURRENCY"
              :error-messages="errorMessages['pair']"
            ></v-text-field>
            <v-text-field
              v-model="amount"
              class="otc-form__amount"
              label="Amount"
              persistent-hint
              hint="Amount bought/sold"
              :error-messages="errorMessages['amount']"
            ></v-text-field>
            <v-text-field
              v-model="rate"
              class="otc-form__rate"
              label="Rate"
              persistent-hint
              hint="Rate of the trade"
              :error-messages="errorMessages['rate']"
            ></v-text-field>
            <v-text-field
              v-model="fee"
              class="otc-form__fee"
              label="Fee"
              persistent-hint
              hint="Fee if any of the trade that occurred"
              :error-messages="errorMessages['fee']"
            ></v-text-field>
            <asset-select
              v-model="feeCurrency"
              label="Fee Currency"
              class="otc-form__fee-currency"
              :rules="assetRules"
              :error-messages="errorMessages['feeCurrency']"
            ></asset-select>
          </v-col>
        </v-row>
        <v-text-field
          v-model="link"
          class="otc-form__link"
          label="Link"
          persistent-hint
          hint="[Optional] A link to the trade. e.g. in an explorer"
          :error-messages="errorMessages['link']"
        ></v-text-field>
        <v-textarea
          v-model="notes"
          class="otc-form__notes"
          label="Additional notes"
          persistent-hint
          hint="[Optional] Additional notes to store for the trade"
          :error-messages="errorMessages['notes']"
        ></v-textarea>
        <!-- <v-card-actions>
            <v-btn
              class="otc-form__buttons__save"
              depressed
              color="primary"
              type="submit"
              @click="addTrade()"
            >
              {{ editMode ? 'Modify Trade' : 'Add Trade' }}
            </v-btn>
            <v-btn
              v-if="editMode"
              class="otc-form__buttons__edit"
              depressed=""
              color="primary"
              @click="cancel"
            >
              Cancel
            </v-btn>
          </v-card-actions> -->
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
import { ApiTrade } from '@/services/types-api';
import { Trade } from '@/store/trades/types';
import { Writeable } from '@/types';
import { snakeToCamel } from '@/utils/conversion';

@Component({
  components: { AssetSelect, DateTimePicker },
  methods: {
    ...mapActions('trades', ['addExternalTrade', 'editExternalTrade'])
  }
})
export default class OtcForm extends Vue {
  @Prop({ required: false, default: null })
  edit!: Trade | null;
  errorMessages: {
    [field: string]: string[];
  } = {};
  addExternalTrade!: (
    trade: Omit<ApiTrade, 'trade_id'>
  ) => Promise<{ result: boolean; error: string }>;
  editExternalTrade!: (
    trade: ApiTrade
  ) => Promise<{ result: boolean; error: string }>;

  private static format = 'DD/MM/YYYY HH:mm';
  readonly assetRules = [
    (v: string) => !!v || 'The fee currency cannot be empty'
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
  type: 'buy' | 'sell' = 'buy';

  mounted() {
    this.setEditMode();
  }

  @Watch('edit')
  onEdit() {
    this.setEditMode();
  }

  private setEditMode() {
    if (!this.edit) {
      this.resetFields();
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
    this.id = trade.tradeId ?? '';
  }

  private resetFields() {
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

  async saveTrade(): Promise<boolean> {
    const tradePayload: Writeable<ApiTrade> = {
      amount: this.amount,
      fee: this.fee,
      fee_currency: this.feeCurrency,
      link: this.link,
      notes: this.notes,
      pair: this.pair,
      rate: this.rate,
      location: 'external',
      timestamp: moment(this.datetime, OtcForm.format).unix(),
      trade_type: this.type,
      trade_id: this.id ? this.id : undefined
    };

    try {
      let result: boolean;
      let error: string;
      if (tradePayload.trade_id === undefined) {
        // add trade
        delete tradePayload.trade_id;
        ({ result, error } = await this.addExternalTrade(tradePayload));
        if (result) {
          this.resetFields();
          return true;
        }
        throw error;
      }

      // edit trade
      ({ result, error } = await this.editExternalTrade(tradePayload));
      if (result) {
        this.resetFields();
        return true;
      }
      throw error;
      // await this.$api.editExternalTrade(tradePayload as Required<ApiTrade>);
    } catch (e) {
      // TODO: put this into a common helper func that always yields something in the form of
      // { [field: string]: string[] } = {} , e.g: { amount: ['Amount is not a number', 'Amount is negative'] }
      const errors = JSON.parse(e.message);
      let errorMessages: { [field: string]: string[] } = {};

      for (const [k, v] of Object.entries(errors)) {
        errorMessages[snakeToCamel(k)] = v as string[];
      }

      this.errorMessages = errorMessages;
      return false;
    }
  }
}
</script>

<style scoped></style>
