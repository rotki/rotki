<template>
  <v-row v-if="!!loan" class="loan-info">
    <v-col cols="12">
      <loan-header class="mt-8 mb-6" :loan="loan" />
      <v-row no-gutters>
        <v-col cols="12" md="6" class="pe-md-4">
          <loan-collateral :loan="loan" />
        </v-col>
        <v-col v-if="isVault" cols="12" md="6" class="ps-md-4 pt-8 pt-md-0">
          <loan-liquidation :loan="loan" />
        </v-col>
        <v-col
          cols="12"
          :md="isVault ? 12 : 6"
          class="pt-8 pt-md-0"
          :class="isVault ? 'pt-md-8' : 'ps-md-4'"
        >
          <loan-debt :loan="loan" />
        </v-col>
      </v-row>
      <v-row v-if="isVault" class="mt-8" no-gutters>
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
      <v-row v-if="isCompound" no-gutters class="mt-8">
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
      <v-row v-if="isAave" no-gutters class="mt-8">
        <v-col cols="12">
          <premium-card v-if="!premium" title="Aave History" />
          <aave-borrowing-details
            v-else
            :loading="aaveHistoryLoading"
            :events="loan.events"
            :owner="loan.owner"
            :total-lost="loan.totalLost"
            :liquidation-earned="loan.liquidationEarned"
          />
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import LoanDisplayMixin from '@/components/defi/loan/loan-display-mixin';
import LoanCollateral from '@/components/defi/loan/LoanCollateral.vue';
import LoanDebt from '@/components/defi/loan/LoanDebt.vue';
import LoanHeader from '@/components/defi/loan/LoanHeader.vue';
import LoanLiquidation from '@/components/defi/loan/LoanLiquidation.vue';
import PremiumCard from '@/components/display/PremiumCard.vue';
import PremiumMixin from '@/mixins/premium-mixin';
import {
  AaveBorrowingDetails,
  CompoundBorrowingDetails,
  VaultEventsList
} from '@/premium/premium';
import { CompoundLoan } from '@/services/defi/types/compound';
import { Section, Status } from '@/store/const';

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
  },
  computed: {
    ...mapGetters(['status'])
  }
})
export default class LoanInfo extends Mixins(PremiumMixin, LoanDisplayMixin) {
  status!: (section: Section) => Status;

  get aaveHistoryLoading(): boolean {
    return this.status(Section.DEFI_AAVE_HISTORY) === Status.LOADING;
  }

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
