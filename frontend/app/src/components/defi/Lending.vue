<template>
  <progress-screen v-if="initialLoading">
    <template #message>
      Please wait while your balances are getting loaded...
    </template>
  </progress-screen>
  <div v-else>
    <v-row>
      <v-col>
        <refresh-header
          :loading="allLoading"
          title="Lending"
          @refresh="refresh()"
        >
          <confirmable-reset
            :loading="allLoading"
            tooltip="Refreshes the data overwriting cached Aave historical entries"
            @reset="reset()"
          >
            This action will overwrite any Aave history cached entries in the DB
            and will fetch everything again. Depending on the number of accounts
            it may take a long time. Are you sure you want to continue?
          </confirmable-reset>
        </refresh-header>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <stat-card-wide :cols="3">
          <template #first-col>
            <stat-card-column>
              <template #title>
                Currently Deposited
              </template>
              <amount-display
                :value="
                  totalLendingDeposit(selectedProtocols, selectedAddresses)
                "
                fiat-currency="USD"
                show-currency="symbol"
              />
            </stat-card-column>
          </template>
          <template #second-col>
            <stat-card-column>
              <template #title>
                Effective Savings Rate
                <v-tooltip bottom max-width="300px">
                  <template #activator="{ on }">
                    <v-icon small class="mb-3 ml-1" v-on="on">
                      fa fa-info-circle
                    </v-icon>
                  </template>
                  <div>
                    The savings rate across all of the protocols in which you
                    are actively lending, weighted based on the relative
                    position in each protocol.
                  </div>
                </v-tooltip>
              </template>
              {{ effectiveInterestRate(selectedProtocols, selectedAddresses) }}
            </stat-card-column>
          </template>
          <template #third-col>
            <stat-card-column lock>
              <template #title>
                Interest Earned
                <premium-lock v-if="!premium" class="d-inline" />
              </template>
              <amount-display
                v-if="premium"
                :loading="initialHistoryLoading"
                :value="totalUsdEarned(selectedProtocols, selectedAddresses)"
                show-currency="symbol"
                fiat-currency="USD"
              />
            </stat-card-column>
          </template>
        </stat-card-wide>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="6">
        <blockchain-account-selector
          v-model="selectedAccount"
          hint
          :usable-accounts="defiAccounts(selectedProtocols)"
        />
      </v-col>
      <v-col cols="6">
        <defi-protocol-selector v-model="protocol" />
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <stat-card title="Assets">
          <lending-asset-table
            :loading="loading"
            :assets="lendingBalances(selectedProtocols, selectedAddresses)"
          />
        </stat-card>
      </v-col>
    </v-row>
    <v-row class="loans__history">
      <v-col cols="12">
        <premium-card v-if="!premium" title="History" />
        <lending-history
          v-else
          :loading="historyLoading"
          :history="lendingHistory(selectedProtocols, selectedAddresses)"
          :floating-precision="floatingPrecision"
          @open-link="openLink($event)"
        />
      </v-col>
    </v-row>
  </div>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import Component from 'vue-class-component';
import { Vue } from 'vue-property-decorator';
import { mapActions, mapGetters, mapState } from 'vuex';
import LendingAssetTable from '@/components/defi/display/LendingAssetTable.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import PremiumCard from '@/components/display/PremiumCard.vue';
import StatCard from '@/components/display/StatCard.vue';
import StatCardColumn from '@/components/display/StatCardColumn.vue';
import StatCardWide from '@/components/display/StatCardWide.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import ConfirmableReset from '@/components/helper/ConfirmableReset.vue';
import DefiProtocolSelector from '@/components/helper/DefiProtocolSelector.vue';
import PremiumLock from '@/components/helper/PremiumLock.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import RefreshHeader from '@/components/helper/RefreshHeader.vue';
import { DEFI_PROTOCOLS } from '@/services/defi/consts';
import { SupportedDefiProtocols } from '@/services/defi/types';
import { Status } from '@/store/const';
import { DefiBalance, DefiLendingHistory } from '@/store/defi/types';
import { Account, DefiAccount } from '@/typing/types';
import { LendingHistory } from '@/utils/premium';

@Component({
  components: {
    ConfirmableReset,
    RefreshHeader,
    LendingAssetTable,
    DefiProtocolSelector,
    StatCardColumn,
    AmountDisplay,
    PremiumCard,
    BlockchainAccountSelector,
    StatCard,
    StatCardWide,
    ProgressScreen,
    PremiumLock,
    LendingHistory
  },
  computed: {
    ...mapState('session', ['premium']),
    ...mapGetters('session', ['floatingPrecision']),
    ...mapState('defi', ['lendingHistoryStatus', 'status']),
    ...mapGetters('defi', [
      'totalUsdEarned',
      'totalLendingDeposit',
      'defiAccounts',
      'effectiveInterestRate',
      'lendingBalances',
      'lendingHistory'
    ])
  },
  methods: {
    ...mapActions('defi', ['fetchLendingHistory', 'fetchLending'])
  }
})
export default class Lending extends Vue {
  premium!: boolean;
  floatingPrecision!: number;
  selectedAccount: Account | null = null;
  totalLendingDeposit!: (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ) => BigNumber;
  defiAccounts!: (protocols: SupportedDefiProtocols[]) => DefiAccount[];
  lendingBalances!: (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ) => DefiBalance[];
  effectiveInterestRate!: (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ) => string;
  protocol: SupportedDefiProtocols | null = null;
  fetchLendingHistory!: (payload?: {
    refresh?: boolean;
    reset?: boolean;
  }) => Promise<void>;
  fetchLending!: (refresh: boolean) => Promise<void>;
  lendingHistoryStatus!: Status;
  status!: Status;
  lendingHistory!: (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ) => DefiLendingHistory<SupportedDefiProtocols>[];
  totalUsdEarned!: (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ) => BigNumber;

  get selectedAddresses(): string[] {
    return this.selectedAccount ? [this.selectedAccount.address] : [];
  }

  get defiAddresses(): string[] {
    return this.defiAccounts(this.selectedProtocols).map(
      ({ address }) => address
    );
  }

  async refresh() {
    await this.fetchLending(true);
    await this.fetchLendingHistory({
      refresh: true
    });
  }

  async reset() {
    await this.fetchLending(true);
    await this.fetchLendingHistory({
      refresh: true,
      reset: true
    });
  }

  async created() {
    const queryElement = this.$route.query['protocol'];
    const protocolIndex = DEFI_PROTOCOLS.findIndex(
      protocol => protocol === queryElement
    );
    if (protocolIndex >= 0) {
      this.protocol = DEFI_PROTOCOLS[protocolIndex];
    }
    await this.fetchLendingHistory();
  }

  get selectedProtocols(): SupportedDefiProtocols[] {
    return this.protocol ? [this.protocol] : [];
  }

  get initialLoading(): boolean {
    return this.status !== Status.LOADED && this.status !== Status.REFRESHING;
  }

  get loading(): boolean {
    return this.status !== Status.LOADED;
  }

  get allLoading(): boolean {
    return (
      this.status !== Status.LOADED ||
      this.lendingHistoryStatus !== Status.LOADED
    );
  }

  get initialHistoryLoading(): boolean {
    return (
      this.lendingHistoryStatus !== Status.LOADED &&
      this.lendingHistoryStatus !== Status.REFRESHING
    );
  }

  get historyLoading(): boolean {
    return this.lendingHistoryStatus !== Status.LOADED;
  }

  openLink(url: string) {
    this.$interop.openUrl(url);
  }
}
</script>
