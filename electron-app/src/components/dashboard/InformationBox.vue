<template>
  <v-card :id="id" color="primary" class="information-box">
    <v-row
      class="information-box__content mx-auto"
      align="center"
      justify="space-between"
    >
      <v-col cols="2">
        <v-icon size="45" color="white" class="information-box__icon">
          fa {{ icon }}
        </v-icon>
      </v-col>
      <v-col cols="10" class="information-box__amount text-right">
        <span class="information-box__amount__number">
          {{
            amount
              | calculatePrice(exchangeRate(currency.ticker_symbol))
              | formatPrice(floatingPrecision)
          }}
        </span>
        <v-icon color="white" class="information-box__amount__currency">
          fa {{ currency.icon }}
        </v-icon>
      </v-col>
    </v-row>
  </v-card>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import { Currency } from '@/model/currency';
import BigNumber from 'bignumber.js';

const { mapState, mapGetters } = createNamespacedHelpers('session');
const mapBalanceGetters = createNamespacedHelpers('balances').mapGetters;

@Component({
  computed: {
    ...mapState(['currency']),
    ...mapGetters(['floatingPrecision']),
    ...mapBalanceGetters(['exchangeRate'])
  }
})
export default class InformationBox extends Vue {
  currency!: Currency;
  floatingPrecision!: number;
  exchangeRate!: (currency: string) => number;

  @Prop({ default: 0 })
  amount!: BigNumber;

  @Prop({ required: true })
  id!: string;

  @Prop({ required: true })
  icon!: string;
}
</script>

<style scoped lang="scss">
.information-box {
  height: 72px;
}

.information-box__icon {
  margin-left: 8px;
}

.information-box__amount {
  color: white;
}

.information-box__amount__number {
  font-size: 34px;
}

.information-box__amount__currency {
  margin-top: -15px;
}

.information-box__actions {
  background-color: white;
}

.information-box__content {
  width: 100%;
}
</style>
