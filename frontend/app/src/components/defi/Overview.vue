<template>
  <stat-card v-if="!summary.balanceUsd" :protocol-icon="icon" class="overview">
    <h3 class="pb-2 d-flex flex-row justify-space-between">
      Borrowing
      <v-btn
        v-if="summary.borrowingUrl"
        color="primary"
        x-small
        icon
        width="20px"
        :to="summary.borrowingUrl"
      >
        <v-icon>fa-external-link-square</v-icon>
      </v-btn>
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
    <h3 class="pb-2 d-flex flex-row justify-space-between">
      Lending
      <v-btn
        v-if="summary.lendingUrl"
        x-small
        icon
        width="20px"
        :to="summary.lendingUrl"
        color="primary"
      >
        <v-icon>fa-external-link-square</v-icon>
      </v-btn>
    </h3>
    <info-row
      title="Total deposit"
      :loading="loading"
      fiat
      :value="summary.totalLendingDepositUsd"
    />
  </stat-card>
  <stat-card v-else :protocol-icon="icon" class="overview">
    <h3 class="pb-2">
      {{ summary.tokenInfo.tokenName }}
    </h3>
    <info-row
      title="Balance"
      :loading="loading"
      fiat
      :value="summary.balanceUsd"
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
    const protocol = this.summary.protocol;
    if (protocol.icon) {
      return `https://${protocol.icon}`;
    }
    return require(`@/assets/images/defi/${protocol.name}.svg`);
  }
}
</script>

<style scoped lang="scss">
.overview {
  min-height: 250px;
  min-width: 300px;
}
</style>
