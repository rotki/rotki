<template>
  <div>
    <v-row>
      <v-col>
        <refresh-header
          :loading="loading"
          title="Defi Overview"
          @refresh="refresh()"
        />
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <stat-card title="MakerDAO">
          <h3 class="pb-2">
            Borrowing
          </h3>
          <info-row
            title="Total collateral"
            :loading="loading"
            fiat
            :value="makerDAOVaultSummary.totalCollateralUsd"
          />
          <info-row
            title="Total debt"
            :loading="loading"
            fiat
            :value="makerDAOVaultSummary.totalDebt"
          />
          <v-divider class="my-4"></v-divider>
          <h3 class="pb-2">Lending</h3>
          <info-row
            title="Total deposit"
            :loading="loading"
            fiat
            :value="totalLendingDeposit(['makerdao'], [])"
          />
        </stat-card>
      </v-col>
    </v-row>
  </div>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import { Component, Vue } from 'vue-property-decorator';
import { mapActions, mapGetters, mapState } from 'vuex';
import InfoRow from '@/components/defi/display/InfoRow.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import StatCard from '@/components/display/StatCard.vue';
import RefreshHeader from '@/components/helper/RefreshHeader.vue';
import { SupportedDefiProtocols } from '@/services/defi/types';
import { Status } from '@/store/defi/status';
import { MakerDAOVaultSummary } from '@/store/defi/types';

@Component({
  components: { RefreshHeader, InfoRow, StatCard, AmountDisplay },
  computed: {
    ...mapState('defi', ['status']),
    ...mapGetters('defi', ['makerDAOVaultSummary', 'totalLendingDeposit'])
  },
  methods: {
    ...mapActions('defi', ['fetchAllDefi'])
  }
})
export default class DecentralizedOverview extends Vue {
  status!: Status;
  totalLendingDeposit!: (
    protocols: SupportedDefiProtocols[],
    addresses: string[]
  ) => BigNumber;
  fetchAllDefi!: (refresh: boolean) => Promise<void>;
  makerDAOVaultSummary!: MakerDAOVaultSummary;
  premium!: boolean;

  get loading(): boolean {
    return this.status !== Status.LOADED;
  }

  async refresh() {
    await this.fetchAllDefi(true);
  }

  async created() {
    await this.fetchAllDefi(false);
  }
}
</script>

<style scoped></style>
