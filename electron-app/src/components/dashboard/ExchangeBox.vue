<template>
  <v-card :id="`${name}_box`" class="exchange-box" color="primary">
    <v-row
      align="center"
      justify="space-between"
      class="exchange-box__information mx-auto"
    >
      <v-col cols="2">
        <v-img
          contain
          size="45"
          class="exchange-box__icon"
          :title="name"
          :class="
            inverted ? 'exchange-box__icon--inverted' : 'exchange-box__icon'
          "
          :src="require(`../../assets/images/${name}.png`)"
        />
      </v-col>
      <v-col cols="10" class="exchange-box__amount text-right">
        <span class="exchange-box__amount__number">
          {{
            amount
              | calculatePrice(exchangeRate(currency.ticker_symbol))
              | formatPrice(floatingPrecision)
          }}
        </span>
        <v-icon color="white" class="exchange-box__amount__currency">
          fa {{ currency.icon }}
        </v-icon>
      </v-col>
    </v-row>
    <v-row align="center" class="exchange-box__footer">
      <v-col cols="12">
        <v-btn
          :id="`exchange-box_details__${name}`"
          :to="`/exchange-balances/${name}`"
          class="exchange-box__footer__view-details mx-auto text-capitalize"
          tile
          outlined
          color="primary"
        >
          View Details
          <v-spacer></v-spacer>
          <v-icon right>
            fa fa-arrow-circle-right
          </v-icon>
        </v-btn>
      </v-col>
    </v-row>
  </v-card>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import { Currency } from '@/model/currency';

const { mapState, mapGetters } = createNamespacedHelpers('session');
const mapBalanceGetters = createNamespacedHelpers('balances').mapGetters;

@Component({
  computed: {
    ...mapState(['currency']),
    ...mapGetters(['floatingPrecision']),
    ...mapBalanceGetters(['exchangeRate'])
  }
})
export default class ExchangeBox extends Vue {
  currency!: Currency;
  floatingPrecision!: number;
  exchangeRate!: (currency: string) => number;

  @Prop({ required: true })
  name!: string;
  @Prop({ required: true })
  amount!: number;

  get inverted(): boolean {
    return ['poloniex', 'binance', 'bitmex'].indexOf(name) > -1;
  }
}
</script>
<style scoped lang="scss">
.exchange-box__icon {
  margin-left: 8px;
  width: 45px;
}

.exchange-box__information {
  width: 100%;
}

.exchange-box__footer {
  background-color: white;
  margin-left: 0 !important;
  margin-right: 0 !important;
}

.exchange-box__footer__view-details {
  border: none !important;
  height: 24px !important;
  width: 100%;
}

.exchange-box__footer .col-12 {
  padding: 4px !important;
}

.exchange-box__amount {
  color: white;
}

.exchange-box__amount__number {
  font-size: 34px;
}

.exchange-box__amount__currency {
  margin-top: -15px;
}
</style>
