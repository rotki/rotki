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
    <v-divider class="my-4" />
    <h4 class="pb-2 d-flex flex-row justify-space-between">
      Details
      <v-dialog v-model="details" scrollable max-width="450px">
        <template #activator="{ on, attrs }">
          <v-btn
            x-small
            icon
            max-width="32px"
            color="primary"
            v-bind="attrs"
            v-on="on"
          >
            <v-icon>fa-external-link-square</v-icon>
          </v-btn>
        </template>
        <v-card>
          <v-card-title>
            <v-img
              aspect-ratio="1"
              :src="icon"
              max-width="32px"
              max-height="32px"
              class="mb-2"
              contain
            />
            <span class="ml-2">
              {{ summary.tokenInfo.tokenName }}
            </span>
          </v-card-title>
          <v-card-subtitle>
            Protocol asset details
          </v-card-subtitle>
          <v-card-text class="overview__details">
            <div v-for="asset in summary.assets" :key="asset.tokenAddress">
              <defi-asset :asset="asset" />
              <v-divider />
            </div>
          </v-card-text>
        </v-card>
      </v-dialog>
    </h4>
  </stat-card>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import CryptoIcon from '@/components/CryptoIcon.vue';
import DefiAsset from '@/components/defi/DefiAsset.vue';
import InfoRow from '@/components/defi/display/InfoRow.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import StatCard from '@/components/display/StatCard.vue';
import { DefiProtocolSummary } from '@/store/defi/types';

@Component({
  components: { DefiAsset, CryptoIcon, AmountDisplay, StatCard, InfoRow }
})
export default class Overview extends Vue {
  @Prop({ required: true, type: Boolean })
  loading!: boolean;
  @Prop({ required: true })
  summary!: DefiProtocolSummary;

  details: boolean = false;

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

  &__details {
    height: 300px;
  }
}
</style>
