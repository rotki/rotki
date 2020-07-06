<template>
  <progress-screen v-if="loading">
    <template #message>
      Please wait while your vaults are getting loaded...
    </template>
  </progress-screen>
  <v-container v-else>
    <v-row>
      <v-col cols="12">
        <h2>Collateralized Loans</h2>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <stat-card-wide :cols="2">
          <template #first-col>
            <dl>
              <dt class="title font-weight-regular">
                Total collateral locked
              </dt>
              <dd class="primary--text text-h5 font-weight-bold">
                <amount-display
                  :value="makerDAOVaultSummary.totalCollateralUsd"
                  show-currency="symbol"
                  fiat-currency="USD"
                ></amount-display>
              </dd>
            </dl>
          </template>
          <template #second-col>
            <dl>
              <dt class="title font-weight-regular">
                Total outstanding debt
              </dt>
              <dd class="primary--text text-h5 font-weight-bold">
                <amount-display
                  :value="makerDAOVaultSummary.totalDebt"
                  asset="DAI"
                ></amount-display>
              </dd>
            </dl>
          </template>
        </stat-card-wide>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <v-card>
          <div class="mx-4 py-4">
            <v-autocomplete
              v-model="selection"
              class="borrowing__vault-selection"
              label="Select Loan"
              item-key="identifier"
              :items="makerDAOVaults"
              item-text="identifier"
              hide-details
              clearable
              :open-on-clear="false"
            ></v-autocomplete>
          </div>
        </v-card>
      </v-col>
    </v-row>
    <loan-info :vault="selectedVault" />
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapActions, mapGetters } from 'vuex';
import LoanInfo from '@/components/defi/LoanInfo.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import StatCard from '@/components/display/StatCard.vue';
import StatCardWide from '@/components/display/StatCardWide.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import {
  MakerDAOVaultModel,
  MakerDAOVaultSummary
} from '@/store/balances/types';
import { MakerDAOVault } from '@/store/defi/types';

@Component({
  computed: {
    ...mapGetters('defi', ['makerDAOVaults', 'makerDAOVaultSummary'])
  },
  methods: {
    ...mapActions('defi', ['fetchMakerDAOVaults', 'fetchMakerDAOVaultDetails'])
  },
  components: {
    AmountDisplay,
    StatCard,
    StatCardWide,
    LoanInfo,
    ProgressScreen
  }
})
export default class Borrowing extends Vue {
  loading: boolean = false;
  selection: number = -1;
  makerDAOVaults!: MakerDAOVaultModel[];
  makerDAOVaultSummary!: MakerDAOVaultSummary;
  fetchMakerDAOVaults!: () => Promise<void>;
  fetchMakerDAOVaultDetails!: () => Promise<void>;

  get selectedVault(): MakerDAOVault | MakerDAOVaultModel | null {
    return (
      this.makerDAOVaults.find(vault => vault.identifier === this.selection) ??
      null
    );
  }

  async mounted() {
    this.loading = true;
    await this.fetchMakerDAOVaults();
    this.loading = false;
    await this.fetchMakerDAOVaultDetails();
  }
}
</script>

<style scoped></style>
