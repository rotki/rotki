<template>
  <progress-screen v-if="loading">
    <template #message>
      Please wait while your balances are getting loaded...
    </template>
  </progress-screen>
  <v-container v-else>
    <v-row>
      <v-col cols="12">
        <stat-card-wide :cols="3">
          <template #first-col>
            <dl>
              <dt class="title font-weight-regular">
                Currently Deposited
              </dt>
              <dd class="primary--text headline font-weight-bold">
                <amount-display
                  :value="totalDepositedUsdAcrossFilteredAccounts"
                  fiat-currency="USD"
                  show-currency="symbol"
                ></amount-display>
              </dd>
            </dl>
          </template>
          <template #second-col>
            <dl>
              <dt class="title font-weight-regular">
                Effective Savings Rate
                <v-tooltip bottom>
                  <template #activator="{ on }">
                    <v-icon small class="mb-3 ml-1" v-on="on">
                      fa fa-info-circle
                    </v-icon>
                  </template>
                  <div>
                    The savings rate across all of the protocols in which<br />
                    you are actively lending, weighted based on the<br />
                    relative position in each protocol.
                  </div>
                </v-tooltip>
              </dt>
              <dd class="primary--text headline font-weight-bold">
                <amount-display :value="currentDSR"></amount-display>
                <span class="lending__percentage-sign">%</span>
              </dd>
            </dl>
          </template>
          <template #third-col>
            <dl>
              <dt
                class="title font-weight-regular d-flex justify-space-between"
              >
                Interest Earned
                <premium-lock v-if="!premium" class="d-inline"></premium-lock>
              </dt>
              <dd
                v-if="premium"
                class="primary--text headline font-weight-bold"
              >
                <amount-display
                  :value="totalUsdGainAcrossFilteredAccounts"
                  show-currency="symbol"
                  fiat-currency="USD"
                ></amount-display>
              </dd>
            </dl>
          </template>
        </stat-card-wide>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <blockchain-account-selector
          :addresses="lendingAddresses"
          @selected-accounts-change="filteredAccounts = $event"
        ></blockchain-account-selector>
      </v-col>
    </v-row>
    <v-row class="loans__history">
      <v-col cols="12">
        <premium-card v-if="!premium" title="History"></premium-card>
        <dsr-movement-history
          v-else
          :history="dsrHistory"
          :account-filter="filteredAccounts.map(x => x.address)"
          :floating-precision="floatingPrecision"
          @open-link="openLink($event)"
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
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import PremiumCard from '@/components/display/PremiumCard.vue';
import StatCard from '@/components/display/StatCard.vue';
import StatCardWide from '@/components/display/StatCardWide.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import PremiumLock from '@/components/helper/PremiumLock.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import { TaskType } from '@/model/task-type';
import { DSRHistory, DSRHistoryItem } from '@/services/types-model';
import {
  Account,
  AccountDSRMovement,
  DSRBalance,
  GeneralAccount,
  Properties
} from '@/typing/types';
import { Zero } from '@/utils/bignumbers';
import { DsrMovementHistory } from '@/utils/premium';

const { mapState, mapGetters: mapSessionGetters } = createNamespacedHelpers(
  'session'
);
const { mapGetters, mapState: mapBalanceState } = createNamespacedHelpers(
  'balances'
);
const { mapGetters: mapTaskGetters } = createNamespacedHelpers('tasks');

@Component({
  components: {
    AmountDisplay,
    PremiumCard,
    BlockchainAccountSelector,
    StatCard,
    StatCardWide,
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
    ]),
    ...mapBalanceState({
      dsrHistoryByAddress: 'dsrHistory'
    })
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
  dsrHistoryByAddress!: DSRHistory;
  isTaskRunning!: (type: TaskType) => boolean;
  filteredAccounts: GeneralAccount[] = [];

  async mounted() {
    await this.$store.dispatch('balances/fetchDSRBalances');
    if (this.premium) {
      await this.$store.dispatch('balances/fetchDSRHistory');
    }
  }

  get lendingAddresses(): Account[] {
    // join addresses from dsrHistory and dsrBalances
    const dsrHistoryAddresses = this.dsrHistory.map(
      dsrEvent => dsrEvent.address
    );
    const dsrBalanceAddresses = this.dsrBalances.map(
      dsrBalance => dsrBalance.address
    );
    return [...dsrHistoryAddresses, ...dsrBalanceAddresses]
      .filter((account, index, accounts) => accounts.indexOf(account) === index)
      .map(address => ({ chain: 'ETH', address: address }));
  }

  get loading(): boolean {
    return (
      this.isTaskRunning(TaskType.DSR_HISTORY) ||
      this.isTaskRunning(TaskType.DSR_BALANCE)
    );
  }

  get totalDepositedUsdAcrossFilteredAccounts(): BigNumber {
    const filteredAccounts = this.filteredAccounts.map(
      account => account.address
    );
    if (filteredAccounts.length === 0) {
      return this.dsrBalances.reduce(
        (sum, { balance }) => sum.plus(balance.usdValue),
        Zero
      );
    }
    const filteredBalances = this.dsrBalances.filter(
      balance => filteredAccounts.indexOf(balance.address) > -1
    );

    return filteredBalances.reduce(
      (sum, { balance }) => sum.plus(balance.usdValue),
      Zero
    );
  }

  get totalGainAcrossFilteredAccounts(): BigNumber {
    return this.calculateTotal('gainSoFar');
  }

  get totalUsdGainAcrossFilteredAccounts(): BigNumber {
    return this.calculateTotal('gainSoFarUsdValue');
  }

  private calculateTotal<K extends Properties<DSRHistoryItem, BigNumber>>(
    property: K
  ): BigNumber {
    const filter = this.filteredAccounts.map(account => account.address);
    let addresses = Object.keys(this.dsrHistoryByAddress);
    if (filter.length !== 0) {
      addresses = addresses.filter(address => filter.indexOf(address) > -1);
    }
    const accounts = addresses.map(account => {
      return {
        address: account,
        ...this.dsrHistoryByAddress[account]
      };
    });

    return accounts.reduce((sum, account) => {
      return sum.plus(account[property]);
    }, Zero);
  }

  openLink(url: string) {
    this.$interop.openUrl(url);
  }
}
</script>
<style scoped lang="scss">
.lending {
  &__percentage-sign {
    margin-left: 5px;
    font-size: 0.8em;
  }
}
</style>
