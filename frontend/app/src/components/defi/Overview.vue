<template>
  <stat-card :icon="icon">
    <h3 class="pb-2">
      Borrowing
    </h3>
    <info-row
      title="Total collateral"
      :loading="loading"
      fiat
      :value="summary.totalCollateralUsd"
    />
    <info-row
      title="Total debt"
      :loading="loading"
      fiat
      :value="summary.totalDebtUsd"
    />
    <v-divider class="my-4"></v-divider>
    <h3 class="pb-2">Lending</h3>
    <info-row
      title="Total deposit"
      :loading="loading"
      fiat
      :value="summary.totalLendingDepositUsd"
    />
  </stat-card>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import InfoRow from '@/components/defi/display/InfoRow.vue';
import StatCard from '@/components/display/StatCard.vue';
import { DefiProtocolSummary } from '@/store/defi/types';

@Component({
  components: { StatCard, InfoRow }
})
export default class Overview extends Vue {
  @Prop({ required: true, type: Boolean })
  loading!: boolean;
  @Prop({ required: true })
  summary!: DefiProtocolSummary;

  get icon(): string {
    return require(`@/assets/images/defi/${this.summary.protocol}.svg`);
  }
}
</script>

<style scoped></style>
