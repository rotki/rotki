<template>
  <progress-screen v-if="loading">
    <template #message>
      Please wait while your balances are getting loaded...
    </template>
  </progress-screen>
  <v-container v-else>
    <v-row>
      <v-col cols="12">
        <stat-card-wide cols="three">
          <template #first-col>
            <dl>
              <dt class="title font-weight-regular">
                Currently Deposited
              </dt>
              <dd class="primary--text headline font-weight-bold">
                <amount-display
                  :value="totalDepositedUsd"
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
                <span style="margin-left: 5px; font-size: 0.8em;">%</span>
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
import {
  GeneralAccount,
  default as BlockchainAccountSelector
} from '@/components/helper/BlockchainAccountSelector.vue';
import PremiumLock from '@/components/helper/PremiumLock.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import { TaskType } from '@/model/task-type';
import { DSRHistory } from '@/services/types-model';
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
      'dsrHistory',
      'dsrHistoryByAddress'
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

  get totalDeposited(): BigNumber {
    return this.dsrBalances.reduce(
      (sum, { balance }) => sum.plus(balance.amount),
      Zero
    );
  }

  get totalDepositedUsd(): BigNumber {
    return this.dsrBalances.reduce(
      (sum, { balance }) => sum.plus(balance.usdValue),
      Zero
    );
  }

  get totalGainAcrossFilteredAccounts(): BigNumber {
    const filteredAccounts = this.filteredAccounts.map(
      account => account.address
    );

    const accountsMap = Object.keys(this.dsrHistoryByAddress).map(account => {
      return {
        address: account,
        ...this.dsrHistoryByAddress[account]
      };
    });

    // Map over all of our dsrHistory, passing those that match the
    // filtered accounts to a reduce to aggregate. If no accounts are
    // filtered then aggregate all of them.
    if (filteredAccounts.length !== 0) {
      return accountsMap
        .filter(account => filteredAccounts.indexOf(account.address) > -1)
        .reduce((sum, account) => {
          return sum.plus(account.gainSoFar);
        }, Zero);
    }
    return accountsMap.reduce((sum, account) => {
      return sum.plus(account.gainSoFar);
    }, Zero);
  }

  get totalUsdGainAcrossFilteredAccounts(): BigNumber {
    const filteredAccounts = this.filteredAccounts.map(
      account => account.address
    );

    const accountsMap = Object.keys(this.dsrHistoryByAddress).map(account => {
      return {
        address: account,
        ...this.dsrHistoryByAddress[account]
      };
    });

    // Map over all of our dsrHistory, passing those that match the
    // filtered accounts to a reduce to aggregate. If no accounts are
    // filtered then aggregate all of them.
    if (filteredAccounts.length !== 0) {
      return accountsMap
        .filter(account => filteredAccounts.indexOf(account.address) > -1)
        .reduce((sum, account) => {
          return sum.plus(account.gainSoFarUsdValue);
        }, Zero);
    }
    return accountsMap.reduce((sum, account) => {
      return sum.plus(account.gainSoFarUsdValue);
    }, Zero);
  }

  openLink(url: string) {
    this.$interop.openUrl(url);
  }
}
</script>
<style scoped lang="scss"></style>
