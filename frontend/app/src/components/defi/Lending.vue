<template>
  <progress-screen v-if="loading">
    <template #message>{{ $t('lending.loading') }}</template>
  </progress-screen>
  <div v-else>
    <v-row>
      <v-col>
        <refresh-header
          :loading="anyRefreshing"
          :title="$t('lending.title')"
          @refresh="refresh()"
        >
          <confirmable-reset
            :loading="anyRefreshing"
            :tooltip="$t('lending.reset_tooltip')"
            @reset="reset()"
          >
            {{ $t('lending.reset_confirm') }}
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
                {{ $t('lending.currently_deposited') }}
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
                {{ $t('lending.effective_interest_rate') }}
                <v-tooltip bottom max-width="300px">
                  <template #activator="{ on }">
                    <v-icon small class="mb-3 ml-1" v-on="on">
                      mdi-information
                    </v-icon>
                  </template>
                  <div>{{ $t('lending.effective_interest_rate_tooltip') }}</div>
                </v-tooltip>
              </template>
              <percentage-display
                justify="start"
                :value="
                  effectiveInterestRate(selectedProtocols, selectedAddresses)
                "
              />
            </stat-card-column>
          </template>
          <template #third-col>
            <stat-card-column lock>
              <template #title>
                {{ $t('lending.profit_earned') }}
                <premium-lock v-if="!premium" class="d-inline" />
              </template>
              <amount-display
                v-if="premium"
                :loading="secondaryLoading"
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
      <v-col cols="12" sm="6">
        <blockchain-account-selector
          v-model="selectedAccount"
          hint
          :usable-accounts="defiAccounts(selectedProtocols)"
        />
      </v-col>
      <v-col cols="12" sm="6">
        <defi-protocol-selector v-model="protocol" />
      </v-col>
    </v-row>
    <v-row v-if="!isYearnVaults">
      <v-col>
        <stat-card :title="$t('lending.assets')">
          <lending-asset-table
            :loading="refreshing"
            :assets="
              aggregatedLendingBalances(selectedProtocols, selectedAddresses)
            "
          />
        </stat-card>
      </v-col>
    </v-row>
    <v-row v-if="isYearnVaults || selectedProtocols.length === 0">
      <v-col>
        <yearn-assets-table
          :loading="refreshing"
          :selected-addresses="selectedAddresses"
        />
      </v-col>
    </v-row>
    <compound-lending-details
      v-if="premium && isCompound"
      :addresses="selectedAddresses"
    />
    <yearn-vaults-profit-details
      v-if="premium && (isYearnVaults || selectedProtocols.length === 0)"
      :profit="yearnVaultsProfit(selectedAddresses)"
    />
    <v-row class="loans__history">
      <v-col cols="12">
        <premium-card v-if="!premium" :title="$t('lending.history')" />
        <lending-history
          v-else
          :loading="secondaryRefreshing"
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
import { Mixins } from 'vue-property-decorator';
import { mapActions, mapGetters, mapState } from 'vuex';
import LendingAssetTable from '@/components/defi/display/LendingAssetTable.vue';
import YearnAssetsTable from '@/components/defi/yearn/YearnAssetsTable.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
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
import StatusMixin from '@/mixins/status-mixin';
import {
  DEFI_COMPOUND,
  DEFI_PROTOCOLS,
  DEFI_YEARN_VAULTS
} from '@/services/defi/consts';
import { SupportedDefiProtocols } from '@/services/defi/types';
import { YearnVaultProfitLoss } from '@/services/defi/types/yearn';
import { Section } from '@/store/const';
import { BaseDefiBalance } from '@/store/defi/types';
import { Account, DefiAccount } from '@/typing/types';
import {
  CompoundLendingDetails,
  LendingHistory,
  YearnVaultsProfitDetails
} from '@/utils/premium';

@Component({
  components: {
    YearnAssetsTable,
    PercentageDisplay,
    CompoundLendingDetails,
    YearnVaultsProfitDetails,
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
    ...mapGetters('defi', [
      'totalUsdEarned',
      'totalLendingDeposit',
      'defiAccounts',
      'effectiveInterestRate',
      'aggregatedLendingBalances',
      'lendingHistory',
      'yearnVaultsProfit'
    ])
  },
  methods: {
    ...mapActions('defi', ['fetchLending'])
  }
})
export default class Lending extends Mixins(StatusMixin) {
  premium!: boolean;
  floatingPrecision!: number;
  selectedAccount: Account | null = null;
  totalLendingDeposit!: (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ) => BigNumber;
  defiAccounts!: (protocols: SupportedDefiProtocols[]) => DefiAccount[];
  aggregatedLendingBalances!: (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ) => BaseDefiBalance[];
  effectiveInterestRate!: (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ) => string;
  protocol: SupportedDefiProtocols | null = null;
  fetchLendingHistory!: (payload?: {
    refresh?: boolean;
    reset?: boolean;
  }) => Promise<void>;
  fetchLending!: (payload?: {
    refresh?: boolean;
    reset?: boolean;
  }) => Promise<void>;
  totalUsdEarned!: (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ) => BigNumber;
  yearnVaultsProfit!: (addresses: string[]) => YearnVaultProfitLoss[];

  section = Section.DEFI_LENDING;
  secondSection = Section.DEFI_LENDING_HISTORY;

  get selectedAddresses(): string[] {
    return this.selectedAccount ? [this.selectedAccount.address] : [];
  }

  get defiAddresses(): string[] {
    return this.defiAccounts(this.selectedProtocols).map(
      ({ address }) => address
    );
  }

  get isCompound(): boolean {
    return (
      this.selectedProtocols.length === 1 &&
      this.selectedProtocols.includes(DEFI_COMPOUND)
    );
  }

  get isYearnVaults(): boolean {
    return (
      this.selectedProtocols.length === 1 &&
      this.selectedProtocols.includes(DEFI_YEARN_VAULTS)
    );
  }

  async refresh() {
    await this.fetchLending({ refresh: true });
  }

  async reset() {
    await this.fetchLending({
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
    await this.fetchLending();
  }

  get selectedProtocols(): SupportedDefiProtocols[] {
    return this.protocol ? [this.protocol] : [];
  }

  openLink(url: string) {
    this.$interop.openUrl(url);
  }
}
</script>
