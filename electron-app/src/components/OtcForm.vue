<template>
  <div>
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
              label="Time"
              persistent-hint
              hint="Time that the trade took place"
            ></date-time-picker>
            <v-text-field
              v-model="pair"
              label="Pair"
              persistent-hint
              hint="Pair for the trade. BASECURRENCY_QUOTE_CURRENCY"
            ></v-text-field>
            <v-radio-group v-model="type" label="Trade type">
              <v-radio label="Buy" value="buy"></v-radio>
              <v-radio label="Sell" value="sell"></v-radio>
            </v-radio-group>
            <v-text-field
              v-model="amount"
              label="Amount"
              persistent-hint
              hint="Amount bought/sold"
            ></v-text-field>
            <v-text-field
              v-model="rate"
              label="Rate"
              persistent-hint
              hint="Rate of the trade"
            ></v-text-field>
            <v-text-field
              v-model="fee"
              label="Fee"
              persistent-hint
              hint="Fee if any that the trade occurred"
            ></v-text-field>
            <v-text-field
              v-model="feeCurrency"
              label="Fee currency"
              persistent-hint
              hint="Currency the fee was payed in"
            ></v-text-field>
            <v-text-field
              v-model="link"
              label="Link"
              persistent-hint
              hint="A link t the trade. e.g. in an explorer"
            ></v-text-field>
            <v-textarea
              v-model="notes"
              label="Additional notes"
              persistent-hint
              hint="Additional notes to store for the trade"
            ></v-textarea>
          </v-card-text>
          <v-card-actions>
            <v-btn
              id="modify_trade_settings"
              depressed
              color="primary"
              type="submit"
              @click="addTrade()"
            >
              {{ editMode ? 'Modify Trade' : 'Add  Trade' }}
            </v-btn>
            <v-btn
              v-if="editMode"
              id="modify_cancel"
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
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import { OtcPayload, OtcTrade } from '@/model/otc-trade';
import DateTimePicker from '@/components/dialogs/DateTimePicker.vue';

@Component({
  components: { DateTimePicker }
})
export default class OtcForm extends Vue {
  @Prop({ required: true })
  editMode!: boolean;
  @Prop({ required: false })
  otcTrade?: OtcTrade;

  id: number = 0;
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

  private static convertTimestamp(timestamp: number): string {
    const date = new Date(timestamp * 1000);
    return (
      ('0' + date.getUTCDate()).slice(-2) +
      '/' +
      ('0' + (date.getUTCMonth() + 1)).slice(-2) +
      '/' +
      date.getUTCFullYear() +
      ' ' +
      ('0' + date.getUTCHours()).slice(-2) +
      ':' +
      ('0' + date.getUTCMinutes()).slice(-2)
    );
  }

  private updateFields(trade: OtcTrade) {
    this.pair = trade.pair;
    this.datetime = OtcForm.convertTimestamp(trade.timestamp);
    this.amount = trade.amount;
    this.rate = trade.rate;
    this.fee = trade.fee;
    this.feeCurrency = trade.fee_currency;
    this.link = trade.link;
    this.notes = trade.notes;
    this.type = trade.trade_type;
    this.id = trade.id;
  }

  private resetFields() {
    this.id = 0;
    this.pair = '';
    this.datetime = '';
    this.amount = '';
    this.rate = '';
    this.fee = '';
    this.feeCurrency = '';
    this.link = '';
    this.notes = '';
    this.type = 'buy';
  }

  addTrade() {
    const trade: OtcPayload = {
      otc_amount: this.amount,
      otc_fee: this.fee,
      otc_fee_currency: this.feeCurrency,
      otc_link: this.link,
      otc_notes: this.notes,
      otc_pair: this.pair,
      otc_rate: this.rate,
      otc_timestamp: this.datetime,
      otc_type: this.type,
      otc_id: this.editMode ? this.id : null
    };

    this.$emit('save', trade);
  }

  @Emit()
  cancel() {}
}
</script>

<style scoped></style>
