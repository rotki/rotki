<template>
  <stat-card
    v-if="!summary.balanceUsd"
    :title="summary.protocol.name"
    :protocol-icon="icon"
    bordered
    class="overview"
  >
    <span
      class="text-subtitle-1 font-weight-bold pb-2 d-flex flex-row justify-space-between"
    >
      {{ $t('overview.stat_card.headers.borrowing') }}
      <v-btn
        v-if="summary.borrowingUrl"
        :to="summary.borrowingUrl"
        icon
        small
        color="primary"
      >
        <v-icon small color="primary">mdi-launch</v-icon>
      </v-btn>
    </span>
    <info-row
      title="Total collateral"
      fiat
      :value="summary.totalCollateralUsd"
    />
    <info-row
      title="Total debt"
      :loading="loading"
      fiat
      :value="summary.totalDebtUsd"
    />
    <v-divider class="my-4" />
    <h4 class="pb-2 d-flex flex-row justify-space-between">
      {{ $t('overview.stat_card.headers.lending') }}
      <v-btn
        v-if="summary.lendingUrl"
        :to="summary.lendingUrl"
        icon
        small
        color="primary"
      >
        <v-icon small color="primary">mdi-launch</v-icon>
      </v-btn>
    </h4>
    <info-row
      title="Total deposit"
      fiat
      :value="summary.totalLendingDepositUsd"
    />
  </stat-card>
  <stat-card
    v-else
    bordered
    :title="summary.protocol.name"
    :protocol-icon="icon"
    class="overview"
  >
    <span class="text-subtitle-1 font-weig$tht-bold pb-2">
      {{ summary.tokenInfo.tokenName }}
    </span>
    <info-row
      title="Balance"
      :loading="loading"
      fiat
      :value="summary.balanceUsd"
    />
    <v-divider class="my-4" />
    <v-dialog v-model="details" scrollable max-width="450px">
      <template #activator="{ on, attrs }">
        <v-btn small v-bind="attrs" block text class="justify-end" v-on="on">
          {{ $t('overview.stat_card.buttons.details') }}
          <v-icon color="primary" right>mdi-launch</v-icon>
        </v-btn>
      </template>
      <v-card>
        <v-card-title class="mb-2">
          <v-img
            aspect-ratio="1"
            :src="icon"
            max-width="32px"
            max-height="32px"
            contain
          />
          <span class="ml-2">
            {{ summary.protocol.name }}
          </span>
        </v-card-title>
        <v-card-subtitle>
          {{ $t('overview.details_dialog.subtitle') }}
        </v-card-subtitle>
        <v-card-text class="overview__details">
          <div v-for="(asset, index) in assets" :key="index">
            <defi-asset :asset="asset" />
            <v-divider />
          </div>
        </v-card-text>
      </v-card>
    </v-dialog>
  </stat-card>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import DefiAsset from '@/components/defi/DefiAsset.vue';
import InfoRow from '@/components/defi/display/InfoRow.vue';
import StatCard from '@/components/display/StatCard.vue';
import { DefiProtocolSummary, DefiAsset as Asset } from '@/store/defi/types';

@Component({
  components: { DefiAsset, StatCard, InfoRow }
})
export default class Overview extends Vue {
  @Prop({ required: true })
  summary!: DefiProtocolSummary;

  details: boolean = false;

  get assets(): Asset[] {
    return this.summary.assets.sort(
      ({ balance: { usdValue } }, { balance: { usdValue: otherUsdValue } }) => {
        if (usdValue.eq(otherUsdValue)) {
          return 0;
        }
        return usdValue.gt(otherUsdValue) ? -1 : 1;
      }
    );
  }

  get icon(): string {
    // until we can check whether a file exists locally, let's make a whitelist of protocols where we prefer our own icon
    const protocolWhitelist: string[] = ['aave', 'makerdao', 'compound'];

    const isWhitelisted: boolean =
      protocolWhitelist.findIndex(
        protocol => protocol == this.summary.protocol.name.toLowerCase()
      ) > -1
        ? true
        : false;

    const protocol = this.summary.protocol;
    if (protocol.icon && !isWhitelisted) {
      return `https://${protocol.icon}`;
    }
    return require(`@/assets/images/defi/${protocol.name.toLocaleLowerCase()}.svg`);
  }
}
</script>

<style scoped lang="scss">
@import '~@/scss/scroll';

.overview {
  min-height: 250px;
  min-width: 300px;

  &__details {
    height: 300px;
    @extend .themed-scrollbar;
  }
}
</style>
