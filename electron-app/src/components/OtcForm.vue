<template>
  <div class="otc-form">
    <v-row>
      <v-col>
        <h1 class="page-header">OTC Trades Management</h1>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <v-card>
          <v-card-title>Register New Trade</v-card-title>
          <v-card-text>
            <date-time-picker
              v-model="datetime"
              class="otc-form__date"
              label="Time"
              persistent-hint
              hint="Time the trade took place"
            ></date-time-picker>
            <v-text-field
              v-model="pair"
              class="otc-form__pair"
              label="Pair"
              persistent-hint
              hint="Pair for the trade. BASECURRENCY_QUOTECURRENCY"
            ></v-text-field>
            <v-radio-group
              v-model="type"
              label="Trade type"
              class="otc-form__type"
            >
              <v-radio label="Buy" value="buy"></v-radio>
              <v-radio label="Sell" value="sell"></v-radio>
            </v-radio-group>
            <v-text-field
              v-model="amount"
              class="otc-form__amount"
              label="Amount"
              persistent-hint
              hint="Amount bought/sold"
            ></v-text-field>
            <v-text-field
              v-model="rate"
              class="otc-form__rate"
              label="Rate"
              persistent-hint
              hint="Rate of the trade"
            ></v-text-field>
            <v-text-field
              v-model="fee"
              class="otc-form__fee"
              label="Fee"
              persistent-hint
              hint="Fee if any of the trade that occurred"
            ></v-text-field>
            <v-text-field
              v-model="feeCurrency"
              class="otc-form__fee-currency"
              label="Fee currency"
              persistent-hint
              hint="Currency the fee was paid in"
            ></v-text-field>
            <v-text-field
              v-model="link"
              class="otc-form__link"
              label="Link"
              persistent-hint
              hint="[Optional] A link to the trade. e.g. in an explorer"
            ></v-text-field>
            <v-textarea
              v-model="notes"
              class="otc-form__notes"
              label="Additional notes"
              persistent-hint
              hint="[Optional] Additional notes to store for the trade"
            ></v-textarea>
          </v-card-text>
          <v-card-actions>
            <v-btn
              class="otc-form__buttons__save"
              depressed
              color="primary"
              type="submit"
              @click="addTrade()"
            >
              {{ editMode ? 'Modify Trade' : 'Add  Trade' }}
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
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script lang="ts">
import moment from 'moment';
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import DateTimePicker from '@/components/dialogs/DateTimePicker.vue';
import { TradePayload } from '@/model/stored-trade';

@Component({
  components: { DateTimePicker }
})
export default class OtcForm extends Vue {
  private static format = 'DD/MM/YYYY HH:mm';

  @Prop({ required: true })
  editMode!: boolean;
  @Prop({ required: false })
  otcTrade: TradePayload | null = null;

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

  @Watch('otcTrade')
  onTradeChange() {
    if (!this.otcTrade) {
      this.resetFields();
    } else {
      this.updateFields(this.otcTrade);
    }
  }

  private updateFields(trade: TradePayload) {
    this.pair = trade.pair;
    this.datetime = moment(trade.timestamp * 1000).format(OtcForm.format);
    this.amount = trade.amount;
    this.rate = trade.rate;
    this.fee = trade.fee;
    this.feeCurrency = trade.fee_currency;
    this.link = trade.link;
    this.notes = trade.notes;
    this.type = trade.trade_type;
    this.id = trade.trade_id ?? '';
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
  }

  addTrade() {
    const trade: TradePayload = {
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
      trade_id: this.editMode ? this.id : undefined
    };

    this.$emit('save', trade);
    this.resetFields();
  }

  @Emit()
  cancel() {
    this.resetFields();
  }
}
</script>

<style scoped></style>
