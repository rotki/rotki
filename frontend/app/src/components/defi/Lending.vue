<template>
  <progress-screen v-if="loading">
    <template #message>
      Please wait while your balances are getting loaded...
    </template>
  </progress-screen>
  <v-container v-else>
    <v-row>
      <v-col cols="12">
        <h2>Overall position</h2>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <stat-card title="Currently Deposited">
          {{ totalDai.dp(decimals) }}

          this will be the total of all assets deposited for lending in
          usdValue->mainCurrency
        </stat-card>
      </v-col>
      <v-col>
        <stat-card>
          <template #title>
            Effective Savings Rate
            <v-tooltip bottom>
              <template #activator="{ on }">
                <v-icon small class="mb-3 ml-1" v-on="on">
                  fa fa-info-circle
                </v-icon>
              </template>
              <div>
                The savings rate across all of the protocols in which you are<br />
                actively lending, weighted based on the relative position<br />
                in each protocol.
              </div>
            </v-tooltip>
          </template>
          {{ currentDSR.dp(2) }}%
        </stat-card>
      </v-col>
      <v-col>
        <stat-card title="Total Interest Earned" :locked="!premium">
          {{ totalGain.dp(decimals) }}
          this will be the total of all interest received from lending in
          usdValue->mainCurrency
        </stat-card>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <blockchain-account-selector
          :addresses="lendingAddresses"
          @selected-accounts-change="filteredAccounts = $event"
        ></blockchain-account-selector>
        <div>
          {{ filteredAccounts }}
        </div>
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
        <stat-card title="approximate $ earned" :locked="!premium">
          {{ accountGainUsdValue(selection.address).dp(decimals) }}
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
import {
  GeneralAccount,
  default as BlockchainAccountSelector
} from '@/components/helper/BlockchainAccountSelector.vue';
// import { GeneralAccount } from '@/components/helper/BlockchainAccountSelector.vue';
import PremiumLock from '@/components/helper/PremiumLock.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import { TaskType } from '@/model/task-type';
import { Account, AccountDSRMovement, DSRBalance } from '@/typing/types';
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
    BlockchainAccountSelector,
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
      'accountGainUsdValue',
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
  accountGainUsdValue!: (address: string) => BigNumber;
  dsrHistory!: AccountDSRMovement[];
  isTaskRunning!: (type: TaskType) => boolean;
  filteredAccounts: GeneralAccount[] = [];

  get lendingAddresses(): Account[] {
    let addresses: Account[] = [];

    // join addresses from dsrHistory and dsrBalances
    const dsrHistoryAddresses = this.dsrHistory.map(dsrEvent => {
      return { chain: 'ETH', address: dsrEvent.address } as Account;
    });

    const dsrBalanceAddresses = this.dsrBalances.map(dsrBalance => {
      return { chain: 'ETH', address: dsrBalance.address } as Account;
    });

    addresses = [...dsrHistoryAddresses, ...dsrBalanceAddresses];

    // remove duplicates
    addresses = addresses.filter(
      (value, index, array) =>
        array.findIndex(
          filterBy =>
            filterBy.chain === value.chain && filterBy.address === value.address
        ) === index
    );

    return addresses;
  }

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
