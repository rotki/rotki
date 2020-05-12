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
            <span>{{ vault.collateralAmount }} </span>
            <span>{{ vault.collateralAsset }}</span>
          </stat-card>
        </v-col>
        <v-col>
          <stat-card title="Debt">
            <span>{{ vault.debtValue.toFormat(2) }}</span>
            <span> DAI </span>
          </stat-card>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <stat-card title="Collateralization Ratio">
            {{ vault.collateralizationRatio }}
          </stat-card>
        </v-col>
        <v-col>
          <stat-card title="Liquidation Rate">
            {{ vault.liquidationRatio }}
          </stat-card>
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import StatCard from '@/components/display/StatCard.vue';
import { MakerDAOVault } from '@/services/types-model';

@Component({
  components: { StatCard }
})
export default class Vault extends Vue {
  @Prop({ required: true })
  vault!: MakerDAOVault | null;
}
</script>

<style scoped lang="scss">
.vault {
  &__identifier {
    font-size: 24px;
  }
}
</style>
