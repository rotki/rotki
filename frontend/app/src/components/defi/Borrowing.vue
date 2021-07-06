<template>
  <progress-screen v-if="loading">
    <template #message>{{ $t('borrowing.loading') }}</template>
  </progress-screen>
  <v-container v-else>
    <v-row class="mt-8">
      <v-col>
        <refresh-header
          :title="$t('borrowing.header')"
          :loading="anyRefreshing"
          @refresh="refresh()"
        >
          <template #actions>
            <active-modules :modules="modules" />
          </template>
        </refresh-header>
      </v-col>
    </v-row>
    <v-row no-gutters class="mt-6">
      <v-col cols="12">
        <stat-card-wide :cols="2">
          <template #first-col>
            <stat-card-column>
              <template #title>
                {{ $t('borrowing.total_collateral_locked') }}
              </template>
              <amount-display
                :value="loanSummary(selectedProtocols).totalCollateralUsd"
                show-currency="symbol"
                fiat-currency="USD"
              />
            </stat-card-column>
          </template>
          <template #second-col>
            <stat-card-column>
              <template #title>
                {{ $t('borrowing.total_outstanding_debt') }}
              </template>
              <amount-display
                :value="loanSummary(selectedProtocols).totalDebt"
                show-currency="symbol"
                fiat-currency="USD"
              />
            </stat-card-column>
          </template>
        </stat-card-wide>
      </v-col>
    </v-row>
    <v-row no-gutters class="mt-8">
      <v-col cols="12" md="6" class="pe-md-4">
        <v-card>
          <div class="mx-4 pt-2">
            <v-autocomplete
              v-model="selection"
              class="borrowing__vault-selection"
              :label="$t('borrowing.select_loan')"
              chips
              item-key="identifier"
              :items="loans(selectedProtocols)"
              item-text="identifier"
              hide-details
              clearable
              :open-on-clear="false"
            >
              <template #selection="{ item }">
                <defi-selector-item :item="item" />
              </template>
              <template #item="{ item }">
                <defi-selector-item :item="item" />
              </template>
            </v-autocomplete>
          </div>
          <v-card-text>{{ $t('borrowing.select_loan_hint') }}</v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="6" class="ps-md-4 pt-8 pt-md-0">
        <defi-protocol-selector v-model="protocol" liabilities />
      </v-col>
    </v-row>
    <loan-info :loan="loan(selection)" />
  </v-container>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { mapActions, mapGetters } from 'vuex';
import ActiveModules from '@/components/defi/ActiveModules.vue';
import DefiSelectorItem from '@/components/defi/DefiSelectorItem.vue';
import LoanInfo from '@/components/defi/loan/LoanInfo.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import StatCardColumn from '@/components/display/StatCardColumn.vue';
import StatCardWide from '@/components/display/StatCardWide.vue';
import DefiProtocolSelector from '@/components/helper/DefiProtocolSelector.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import RefreshHeader from '@/components/helper/RefreshHeader.vue';
import StatusMixin from '@/mixins/status-mixin';
import { DEFI_PROTOCOLS } from '@/services/defi/consts';
import { SupportedDefiProtocols } from '@/services/defi/types';
import {
  MODULE_AAVE,
  MODULE_COMPOUND,
  MODULE_MAKERDAO_VAULTS
} from '@/services/session/consts';
import { SupportedModules } from '@/services/session/types';
import { Section } from '@/store/const';
import {
  AaveLoan,
  DefiLoan,
  LoanSummary,
  MakerDAOVaultModel
} from '@/store/defi/types';

@Component({
  computed: {
    ...mapGetters('defi', ['loan', 'loans', 'loanSummary'])
  },
  methods: {
    ...mapActions('defi', ['fetchBorrowing'])
  },
  components: {
    ActiveModules,
    DefiSelectorItem,
    DefiProtocolSelector,
    RefreshHeader,
    StatCardColumn,
    AmountDisplay,
    StatCardWide,
    LoanInfo,
    ProgressScreen
  }
})
export default class Borrowing extends Mixins(StatusMixin) {
  selection?: string = '';
  loan!: (identifier?: string) => MakerDAOVaultModel | AaveLoan | null;
  loans!: (protocol: SupportedDefiProtocols[]) => DefiLoan[];
  loanSummary!: (protocol: SupportedDefiProtocols[]) => LoanSummary;
  fetchBorrowing!: (refreshing: boolean) => Promise<void>;
  protocol: SupportedDefiProtocols | null = null;

  section = Section.DEFI_BORROWING;
  secondSection = Section.DEFI_BORROWING_HISTORY;

  readonly modules: SupportedModules[] = [
    MODULE_AAVE,
    MODULE_COMPOUND,
    MODULE_MAKERDAO_VAULTS
  ];

  get selectedProtocols(): SupportedDefiProtocols[] {
    return this.protocol ? [this.protocol] : [];
  }

  async created() {
    const queryElement = this.$route.query['protocol'];
    const protocolIndex = DEFI_PROTOCOLS.findIndex(
      protocol => protocol === queryElement
    );
    if (protocolIndex >= 0) {
      this.protocol = DEFI_PROTOCOLS[protocolIndex];
    }
    await this.fetchBorrowing(false);
  }

  async refresh() {
    await this.fetchBorrowing(true);
  }
}
</script>
