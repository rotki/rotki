<template>
  <progress-screen v-if="loading">
    <template #message>
      Please wait while your balances are getting loaded...
    </template>
  </progress-screen>
  <v-container v-else>
    <v-row>
      <v-col cols="12">
        <h2>MakerDAO DSR</h2>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12" class="loans__cards">
        <v-card>
          <v-card-title>
            Current DSR
          </v-card-title>
          <v-card-text> {{ currentDSR.dp(2) }}% </v-card-text>
        </v-card>
        <v-card>
          <v-card-title>
            Total DAI locked
          </v-card-title>
          <v-card-text>
            {{ totalDai.dp(decimals) }}
          </v-card-text>
        </v-card>
        <v-card>
          <v-card-title>
            Total DAI earned
            <v-spacer v-if="!premium"></v-spacer>
            <premium-lock v-if="!premium"></premium-lock>
          </v-card-title>
          <v-card-text>
            <span v-if="premium">
              {{ totalGain.dp(decimals) }}
            </span>
            <span v-else> </span>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <v-select
          v-model="selection"
          class="loans__account-selector"
          label="Account"
          return-object
          :items="dsrBalances"
          item-text="address"
        ></v-select>
      </v-col>
    </v-row>
    <v-row v-if="!!selection">
      <v-col cols="12" class="loans__cards">
        <v-card>
          <v-card-title>
            DAI locked
          </v-card-title>
          <v-card-text>
            {{ selection.balance.dp(decimals) }}
          </v-card-text>
        </v-card>
        <v-card>
          <v-card-title>
            DAI earned
            <v-spacer v-if="!premium"></v-spacer>
            <premium-lock v-if="!premium"></premium-lock>
          </v-card-title>
          <v-card-text>
            <span v-if="premium">
              {{ accountGain(selection.address).dp(decimals) }}
            </span>
            <span v-else> </span>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    <v-row class="loans__history">
      <v-col cols="12">
        <v-card v-if="!premium">
          <v-card-title>
            History
            <v-spacer></v-spacer>
            <premium-lock></premium-lock>
          </v-card-title>
        </v-card>
        <dsr-movement-history
          v-else
          :history="dsrHistory"
          :floating-precision="floatingPrecision"
        ></dsr-movement-history>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import Component from 'vue-class-component';
import { Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import PremiumLock from '@/components/helper/PremiumLock.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import { TaskType } from '@/model/task';
import { AccountDSRMovement, DSRBalance } from '@/typing/types';
import { Zero } from '@/utils/bignumbers';
import { DsrMovementHistory } from '@/utils/premium';

const { mapState, mapGetters: mapSessionGetters } = createNamespacedHelpers(
  'session'
);
const { mapGetters } = createNamespacedHelpers('balances');
const { mapGetters: mapTaskGetters } = createNamespacedHelpers('tasks');

@Component({
  components: {
    ProgressScreen,
    PremiumLock,
    DsrMovementHistory
  },
  computed: {
    ...mapTaskGetters(['isTaskRunning']),
    ...mapState(['premium']),
    ...mapSessionGetters(['floatingPrecision']),
    ...mapGetters([
      'currentDSR',
      'dsrBalances',
      'totalGain',
      'accountGain',
      'dsrHistory'
    ])
  }
})
export default class Loans extends Vue {
  premium!: boolean;
  floatingPrecision!: number;
  currentDSR!: BigNumber;
  dsrBalances!: DSRBalance[];
  selection: DSRBalance | null = null;
  totalGain!: BigNumber;
  accountGain!: (address: string) => BigNumber;
  dsrHistory!: AccountDSRMovement[];
  isTaskRunning!: (type: TaskType) => boolean;

  get loading(): boolean {
    return (
      this.isTaskRunning(TaskType.DSR_HISTORY) ||
      this.isTaskRunning(TaskType.DSR_BALANCE)
    );
  }

  readonly decimals: number = 8;

  get totalDai(): BigNumber {
    return this.dsrBalances.reduce(
      (sum, { balance }) => sum.plus(balance),
      Zero
    );
  }

  async mounted() {
    await this.$store.dispatch('balances/fetchDSRBalances');
    if (this.premium) {
      await this.$store.dispatch('balances/fetchDSRHistory');
    }
  }
}
</script>

<style scoped lang="scss">
.loans {
  &__account-selector {
    padding-left: 12px;
    padding-right: 12px;
  }

  &__history {
    padding-left: 12px;
    padding-right: 12px;
  }

  &__cards {
    width: 100%;
    display: flex;
    flex-direction: row;
    align-content: space-evenly;
    ::v-deep {
      .v-card {
        margin: 12px;
        width: 100%;
        padding-bottom: 12px;
        padding-left: 12px;
        padding-right: 12px;
        .v-card__title {
          font-size: 16px;
          color: #646464;
        }
        .v-card__text {
          padding-top: 12px;
          font-weight: 500;
          font-size: 32px;
        }
      }
    }
  }
}
</style>
