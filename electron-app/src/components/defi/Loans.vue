<template>
  <v-card>
    <v-card-title>
      MakerDAO DSR
    </v-card-title>
    <v-card-text>
      <div class="loans__current-dsr">
        <span>Current DSR:</span> {{ currentDSR.dp(2) }}%
      </div>
      <div class="loans__total-dai">
        <span>Total DAI:</span> {{ totalDai.dp(floatingPrecision) }}
      </div>
      <div v-if="premium">
        <span>Total DAI earned:</span>
      </div>
      <v-select
        v-model="selection"
        return-object
        :items="dsrBalances"
        item-text="address"
      ></v-select>

      <div v-if="!!selection">
        <div class="loans__account__dai-locked">
          <span>DAI locked:</span> {{ selection.balance.dp(floatingPrecision) }}
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { Vue } from 'vue-property-decorator';
import Component from 'vue-class-component';
import { createNamespacedHelpers } from 'vuex';
import BigNumber from 'bignumber.js';
import { DSRBalance } from '@/typing/types';
import { Zero } from '@/utils/bignumbers';

const { mapState, mapGetters: mapSessionGetters } = createNamespacedHelpers(
  'session'
);
const { mapGetters } = createNamespacedHelpers('balances');

@Component({
  computed: {
    ...mapState(['premium']),
    ...mapSessionGetters(['floatingPrecision']),
    ...mapGetters(['currentDSR', 'dsrBalances'])
  }
})
export default class Loans extends Vue {
  premium!: boolean;
  floatingPrecision!: number;
  currentDSR!: BigNumber;
  dsrBalances!: DSRBalance[];
  selection: DSRBalance | null = null;

  get totalDai(): BigNumber {
    return this.dsrBalances.reduce(
      (sum, { balance }) => sum.plus(balance),
      Zero
    );
  }

  async mounted() {
    await this.$store.dispatch('balances/fetchDSRBalances');
  }
}
</script>

<style scoped lang="scss">
.loans {
  &__current-dsr {
    font-size: 18px;
    padding-top: 8px;
    padding-bottom: 8px;

    & span {
      font-weight: 500;
    }
  }
  &__total-dai {
    font-size: 18px;
    padding-top: 8px;
    padding-bottom: 8px;

    & span {
      font-weight: 500;
    }
  }

  &__account {
    &__dai-locked {
      font-size: 18px;
      padding-top: 8px;
      padding-bottom: 8px;

      & span {
        font-weight: 500;
      }
    }
  }
}
</style>
