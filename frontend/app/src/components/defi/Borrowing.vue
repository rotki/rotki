<template>
  <progress-screen v-if="loading">
    <template #message>
      Please wait while your vaults are getting loaded...
    </template>
  </progress-screen>
  <div v-else>
    <v-row>
      <v-col cols="12">
        <h2>Collateralized Loans</h2>
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
                :value="makerDAOVaultSummary.totalCollateralUsd"
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
                :value="makerDAOVaultSummary.totalDebt"
                asset="DAI"
              ></amount-display>
            </stat-card-column>
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
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import LoanInfo from '@/components/defi/maker/LoanInfo.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import StatCard from '@/components/display/StatCard.vue';
import StatCardColumn from '@/components/display/StatCardColumn.vue';
import StatCardWide from '@/components/display/StatCardWide.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import {
  MakerDAOVault,
  MakerDAOVaultModel,
  MakerDAOVaultSummary
} from '@/store/defi/types';

@Component({
  computed: {
    ...mapGetters('defi', ['makerDAOVaults', 'makerDAOVaultSummary'])
  },
  components: {
    StatCardColumn,
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

  get selectedVault(): MakerDAOVault | MakerDAOVaultModel | null {
    return (
      this.makerDAOVaults.find(vault => vault.identifier === this.selection) ??
      null
    );
  }
}
</script>

<style scoped></style>
