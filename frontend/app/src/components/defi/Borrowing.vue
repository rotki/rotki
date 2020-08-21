<template>
  <progress-screen v-if="loading">
    <template #message>
      Please wait while your vaults are getting loaded...
    </template>
  </progress-screen>
  <div v-else>
    <v-row>
      <v-col cols="12">
        <refresh-header
          title="Collateralized Loans"
          :loading="refreshing"
          @refresh="refresh()"
        />
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <stat-card-wide :cols="2">
          <template #first-col>
            <stat-card-column>
              <template #title>
                Total collateral locked
              </template>
              <amount-display
                :value="loanSummary(selectedProtocols).totalCollateralUsd"
                show-currency="symbol"
                fiat-currency="USD"
              ></amount-display>
            </stat-card-column>
          </template>
          <template #second-col>
            <stat-card-column>
              <template #title>
                Total outstanding debt
              </template>
              <amount-display
                :value="loanSummary(selectedProtocols).totalDebt"
                show-currency="symbol"
                fiat-currency="USD"
              ></amount-display>
            </stat-card-column>
          </template>
        </stat-card-wide>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="6">
        <v-card>
          <div class="mx-4 pt-2">
            <v-autocomplete
              v-model="selection"
              class="borrowing__vault-selection"
              label="Select Loan"
              chips
              item-key="identifier"
              :items="loans(selectedProtocols)"
              item-text="identifier"
              hide-details
              clearable
              :open-on-clear="false"
            >
              <template #selection="{item}">
                <v-img
                  aspect-ratio="1"
                  contain
                  position="left"
                  max-width="26px"
                  max-height="24px"
                  :src="require(`@/assets/images/defi/${item.protocol}.svg`)"
                />
                <span class="ml-3">{{ item.identifier }}</span>
              </template>
              <template #item="{item}">
                <v-img
                  aspect-ratio="1"
                  contain
                  position="left"
                  max-width="26px"
                  max-height="24px"
                  :src="require(`@/assets/images/defi/${item.protocol}.svg`)"
                />
                <span class="ml-3">{{ item.identifier }}</span>
              </template>
            </v-autocomplete>
          </div>
          <v-card-text>
            Please select a loan to see information
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6">
        <defi-protocol-selector v-model="protocol" />
      </v-col>
    </v-row>
    <loan-info :loan="loan(selection)" />
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapActions, mapGetters, mapState } from 'vuex';
import LoanInfo from '@/components/defi/loan/LoanInfo.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import StatCardColumn from '@/components/display/StatCardColumn.vue';
import StatCardWide from '@/components/display/StatCardWide.vue';
import DefiProtocolSelector from '@/components/helper/DefiProtocolSelector.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import RefreshHeader from '@/components/helper/RefreshHeader.vue';
import { DEFI_PROTOCOLS, SupportedDefiProtocols } from '@/services/defi/types';
import { Status } from '@/store/const';
import {
  AaveLoan,
  DefiLoan,
  LoanSummary,
  MakerDAOVaultModel
} from '@/store/defi/types';

@Component({
  computed: {
    ...mapGetters('defi', ['loan', 'loans', 'loanSummary']),
    ...mapState('defi', ['borrowingHistoryStatus', 'status'])
  },
  methods: {
    ...mapActions('defi', ['fetchBorrowingHistory', 'fetchBorrowing'])
  },
  components: {
    DefiProtocolSelector,
    RefreshHeader,
    StatCardColumn,
    AmountDisplay,
    StatCardWide,
    LoanInfo,
    ProgressScreen
  }
})
export default class Borrowing extends Vue {
  selection?: string = '';
  loan!: (identifier?: string) => MakerDAOVaultModel | AaveLoan | null;
  loans!: (protocol: SupportedDefiProtocols[]) => DefiLoan[];
  loanSummary!: (protocol: SupportedDefiProtocols[]) => LoanSummary;
  fetchBorrowing!: (refreshing: boolean) => Promise<void>;
  fetchBorrowingHistory!: (refreshing: boolean) => Promise<void>;
  status!: Status;
  borrowingHistoryStatus!: Status;
  protocol: SupportedDefiProtocols | null = null;

  get selectedProtocols(): SupportedDefiProtocols[] {
    return this.protocol ? [this.protocol] : [];
  }

  get refreshing(): boolean {
    return (
      this.status !== Status.LOADED ||
      this.borrowingHistoryStatus !== Status.LOADED
    );
  }

  get loading(): boolean {
    return this.status !== Status.LOADED && this.status !== Status.REFRESHING;
  }

  async created() {
    const queryElement = this.$route.query['protocol'];
    const protocolIndex = DEFI_PROTOCOLS.findIndex(
      protocol => protocol === queryElement
    );
    if (protocolIndex >= 0) {
      this.protocol = DEFI_PROTOCOLS[protocolIndex];
    }
    await this.fetchBorrowingHistory(false);
  }

  async refresh() {
    await this.fetchBorrowing(true);
    await this.fetchBorrowingHistory(true);
  }
}
</script>

<style scoped></style>
