<template>
  <v-row v-if="!!loan" class="loan-info">
    <v-col cols="12">
      <loan-header :loan="loan" />
      <v-row>
        <v-col cols="12" md="6">
          <loan-collateral :loan="loan" />
        </v-col>
        <v-col v-if="isVault" cols="12" md="6">
          <loan-liquidation :loan="loan" />
        </v-col>
        <v-col cols="12" :md="isVault ? 12 : 6">
          <loan-debt :loan="loan" />
        </v-col>
      </v-row>
      <v-row v-if="isVault" class="mt-6">
        <v-col cols="12">
          <premium-card v-if="!premium" title="Borrowing History" />
          <vault-events-list
            v-else
            :asset="loan.collateral.asset"
            :events="loan.events"
            :creation="loan.creationTs"
            @open-link="openLink($event)"
          />
        </v-col>
      </v-row>
      <v-row v-if="isCompound" no-gutters>
        <v-col cols="12">
          <premium-card v-if="!premium" title="Compound History" />
          <compound-borrowing-details
            v-else
            :events="loan.events"
            :owner="loan.owner"
            :assets="assets"
          />
        </v-col>
      </v-row>
      <v-row v-if="isAave" no-gutters>
        <v-col cols="12">
          <premium-card v-if="!premium" title="Aave History" />
          <aave-borrowing-details
            v-else
            :events="loan.events"
            :owner="loan.owner"
            :total-lost="loan.totalLost"
          />
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import LoanDisplayMixin from '@/components/defi/loan/loan-display-mixin';
import LoanCollateral from '@/components/defi/loan/LoanCollateral.vue';
import LoanDebt from '@/components/defi/loan/LoanDebt.vue';
import LoanHeader from '@/components/defi/loan/LoanHeader.vue';
import LoanLiquidation from '@/components/defi/loan/LoanLiquidation.vue';
import PremiumCard from '@/components/display/PremiumCard.vue';
import PremiumMixin from '@/mixins/premium-mixin';
import { CompoundLoan } from '@/services/defi/types/compound';
import {
  AaveBorrowingDetails,
  CompoundBorrowingDetails,
  VaultEventsList
} from '@/utils/premium';

@Component({
  components: {
    CompoundBorrowingDetails,
    LoanCollateral,
    LoanDebt,
    LoanHeader,
    LoanLiquidation,
    PremiumCard,
    VaultEventsList,
    AaveBorrowingDetails
  }
})
export default class LoanInfo extends Mixins(PremiumMixin, LoanDisplayMixin) {
  get assets(): string[] {
    const assets = this.loan?.asset ? [this.loan.asset] : [];

    if (this.isCompound && (this.loan as CompoundLoan).events.length > 0) {
      const { events } = this.loan as CompoundLoan;
      const toAssets: string[] = events
        .map(({ toAsset }) => toAsset ?? '')
        .filter(
          (value, index, array) => !!value && array.indexOf(value) === index
        );
      assets.push(...toAssets);
    }

    return assets;
  }
  openLink(url: string) {
    this.$interop.openUrl(url);
  }
}
</script>
