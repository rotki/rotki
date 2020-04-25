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
          <amount-display
            show-currency="symbol"
            usd-value
            :value="amount"
          ></amount-display>
        </span>
      </v-col>
    </v-row>
    <v-row
      v-if="blockchain"
      align="center"
      justify="end"
      class="information-box__footer"
    >
      <v-col cols="12">
        <v-row justify="end" no-gutters>
          <v-tooltip bottom>
            <template #activator="{ on }">
              <v-btn text icon color="primary" @click="refresh()" v-on="on">
                <v-icon>
                  fa-refresh
                </v-icon>
              </v-btn>
            </template>
            <span>
              Refreshes the blockchain balances ignoring any cached entries
            </span>
          </v-tooltip>
        </v-row>
      </v-col>
    </v-row>
  </v-card>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import { Component, Prop, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import { Currency } from '@/model/currency';
import { BlockchainBalancePayload } from '@/store/balances/actions';

const { mapGetters } = createNamespacedHelpers('session');
const { mapGetters: mapBalanceGetters } = createNamespacedHelpers('balances');

@Component({
  components: {
    AmountDisplay
  },
  computed: {
    ...mapGetters(['floatingPrecision', 'currency']),
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

  @Prop({ default: false, type: Boolean })
  blockchain!: boolean;

  refresh() {
    this.$store.dispatch('balances/fetchBlockchainBalances', {
      ignoreCache: true
    } as BlockchainBalancePayload);
  }
}
</script>

<style scoped lang="scss">
.information-box__currency__symbol {
  font-size: 2em;
}

.information-box {
  min-height: 72px;
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

.information-box__footer {
  background-color: white;
  margin-left: 0 !important;
  margin-right: 0 !important;
  ::v-deep .col {
    padding-top: 4px !important;
    padding-bottom: 4px !important;
    padding-right: 10px !important;
  }
}
</style>
