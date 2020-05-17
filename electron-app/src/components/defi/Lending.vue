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
      <v-col>
        <stat-card title="Current DSR"> {{ currentDSR.dp(2) }}% </stat-card>
      </v-col>
      <v-col>
        <stat-card title="Total DAI locked">
          {{ totalDai.dp(decimals) }}
        </stat-card>
      </v-col>
      <v-col>
        <stat-card title="Total DAI earned" :locked="!premium">
          {{ totalGain.dp(decimals) }}
        </stat-card>
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
      <v-col>
        <stat-card title="DAI locked">
          {{ selection.balance.dp(decimals) }}
        </stat-card>
      </v-col>
      <v-col>
        <stat-card title="DAI earned" :locked="!premium">
          {{ accountGain(selection.address).dp(decimals) }}
        </stat-card>
      </v-col>
    </v-row>
    <v-row class="loans__history">
      <v-col cols="12">
        <premium-card v-if="!premium" title="History"></premium-card>
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
import PremiumCard from '@/components/display/PremiumCard.vue';
import StatCard from '@/components/display/StatCard.vue';
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
    PremiumCard,
    StatCard,
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
export default class Lending extends Vue {
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
