<template>
  <progress-screen v-if="loading">
    <template #message>
      Please wait while your vaults are getting loaded...
    </template>
  </progress-screen>
  <v-container v-else>
    <v-row>
      <v-col cols="12">
        <h2>MakerDAO Vaults</h2>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <stat-card title="Total collateral locked">
          <amount-display
            :value="makerDAOVaultSummary.totalCollateralUsd"
            show-currency="symbol"
            fiat-currency="USD"
          ></amount-display>
        </stat-card>
      </v-col>
      <v-col>
        <stat-card title="Total debt">
          <amount-display
            :value="makerDAOVaultSummary.totalDebt"
            asset="DAI"
          ></amount-display>
        </stat-card>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <v-autocomplete
          v-model="selection"
          class="borrowing__vault-selection"
          label="Vault"
          return-object
          :items="makerDAOVaults"
          item-text="identifier"
        ></v-autocomplete>
      </v-col>
    </v-row>
    <vault :vault="selection" />
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import Vault from '@/components/defi/Vault.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import StatCard from '@/components/display/StatCard.vue';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import {
  MakerDAOVaultModel,
  MakerDAOVaultSummary
} from '@/store/balances/types';

const { mapGetters } = createNamespacedHelpers('balances');

@Component({
  computed: {
    ...mapGetters(['makerDAOVaults', 'makerDAOVaultSummary'])
  },
  components: { AmountDisplay, StatCard, Vault, ProgressScreen }
})
export default class Borrowing extends Vue {
  loading: boolean = false;
  selection: MakerDAOVaultModel | null = null;
  makerDAOVaults!: MakerDAOVaultModel[];
  makerDAOVaultSummary!: MakerDAOVaultSummary;

  async mounted() {
    await this.$store.dispatch('balances/fetchMakerDAOVaults');
  }
}
</script>

<style scoped></style>
