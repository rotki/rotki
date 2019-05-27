<template>
  <div>
    <v-layout>
      <v-flex>
        <h1 class="page-header">OTC Trades Management</h1>
      </v-flex>
    </v-layout>
    <v-layout>
      <v-flex>
        <v-card>
          <v-toolbar card>Register New Trade</v-toolbar>
          <v-card-text>
            <v-text-field
              v-model="time"
              label="Time"
              persistent-hint
              hint="Time that the trade took place"
            ></v-text-field>
            <v-text-field
              v-model="pair"
              label="Pair"
              persistent-hint
              hint="Pair for the trade. BASECURRENCY_QUOTE_CURRENCY"
            ></v-text-field>
            <v-radio-group v-model="type" label="trade type">
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
          </v-card-actions>
        </v-card>
      </v-flex>
    </v-layout>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { OtcTrade } from '@/model/otc-trade';

@Component({})
export default class OtcForm extends Vue {
  @Prop({ required: true })
  editMode!: boolean;

  pair: string = '';
  timestamp: number = 0;
  amount: string = '';
  rate: string = '';
  fee: string = '';
  feeCurrency: string = '';
  link: string = '';
  notes: string = '';
  type: 'buy' | 'sell' = 'buy';

  addTrade() {
    const trade: OtcTrade = {
      amount: this.amount,
      fee: this.fee,
      fee_currency: this.feeCurrency,
      link: this.link,
      notes: this.notes,
      pair: this.pair,
      rate: this.rate,
      timestamp: this.timestamp,
      type: this.type,
      id: 0
    };

    this.$emit('save', trade);
  }
}
</script>

<style scoped></style>
