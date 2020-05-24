<template>
  <v-row v-if="!!vault" class="vault">
    <v-col cols="12">
      <v-row>
        <v-col>
          <h1>{{ vault.name }}</h1>
          <div class="vault__identifier">{{ vault.identifier }}</div>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <stat-card title="Collateral">
            <amount-display
              :value="vault.collateralAmount"
              :asset="vault.collateralAsset"
            ></amount-display>
          </stat-card>
        </v-col>
        <v-col>
          <stat-card title="Debt">
            <amount-display
              :value="vault.debtValue"
              asset="DAI"
            ></amount-display>
          </stat-card>
        </v-col>
        <v-col>
          <stat-card title="Collateralization ratio">
            {{ vault.collateralizationRatio }}
          </stat-card>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <stat-card title="Liquidation rate">
            {{ vault.liquidationRatio }}
          </stat-card>
        </v-col>
        <v-col>
          <stat-card title="Liquidation price">
            <amount-display :value="vault.liquidationPrice"></amount-display>
          </stat-card>
        </v-col>
        <v-col>
          <stat-card title="Collateral value">
            <amount-display
              :value="vault.collateralUsdValue"
              fiat-currency="USD"
              show-currency="symbol"
            ></amount-display>
          </stat-card>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <stat-card
            title="Created"
            :locked="!premium"
            :loading="!vault.creationTs"
          >
            {{ vault.creationTs | formatDate(dateDisplayFormat) }}
          </stat-card>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <stat-card
            title="Total interest owned"
            :locked="!premium"
            :loading="!vault.totalInterestOwed"
          >
            <amount-display
              :value="vault.totalInterestOwed"
              asset="DAI"
            ></amount-display>
          </stat-card>
        </v-col>
        <v-col
          v-if="
            vault.totalLiquidatedAmount && vault.totalLiquidatedAmount.gt(0)
          "
        >
          <stat-card
            title="Total liquidated amount"
            :locked="!premium"
            :loading="!vault.totalLiquidatedAmount"
          >
            <amount-display
              :value="vault.totalLiquidatedAmount"
              :asset="vault.collateralAsset"
            ></amount-display>
          </stat-card>
        </v-col>
        <v-col
          v-if="vault.totalLiquidatedUsd && vault.totalLiquidatedUsd.gt(0)"
        >
          <stat-card title="Total liquidated value" :locked="!premium">
            <amount-display
              :value="vault.totalLiquidatedUsd"
              show-currency="symbol"
              fiat-currency="USD"
            ></amount-display>
          </stat-card>
        </v-col>
      </v-row>
      <v-row v-if="vault.totalLiquidatedUsd && vault.totalLiquidatedUsd.gt(0)">
        <v-col>
          <stat-card title="Total value lost" :locked="!premium">
            <amount-display
              :value="vault.totalLiquidatedUsd.plus(vault.totalInterestOwed)"
              show-currency="symbol"
              fiat-currency="USD"
            ></amount-display>
          </stat-card>
        </v-col>
      </v-row>
      <v-row>
        <v-col cols="12">
          <premium-card v-if="!premium" title="Actions"></premium-card>
          <vault-events-list
            v-else
            :asset="vault.collateralAsset"
            :events="vault.events"
          ></vault-events-list>
        </v-col>
      </v-row>
    </v-col>
  </v-row>
  <v-row v-else align="center" justify="center">
    <v-col>
      <span class="font-weight-light subtitle-2">
        Please select a Vault to see information
      </span>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import PremiumCard from '@/components/display/PremiumCard.vue';
import StatCard from '@/components/display/StatCard.vue';
import { MakerDAOVault } from '@/services/types-model';
import { MakerDAOVaultModel } from '@/store/balances/types';
import { VaultEventsList } from '@/utils/premium';

const { mapState, mapGetters } = createNamespacedHelpers('session');

@Component({
  components: { PremiumCard, AmountDisplay, StatCard, VaultEventsList },
  computed: {
    ...mapState(['premium']),
    ...mapGetters(['dateDisplayFormat'])
  }
})
export default class Vault extends Vue {
  @Prop({ required: true })
  vault!: MakerDAOVault | MakerDAOVaultModel | null;

  premium!: boolean;
  dateDisplayFormat!: string;
}
</script>

<style scoped lang="scss">
.vault {
  &__identifier {
    font-size: 24px;
  }
}
</style>
