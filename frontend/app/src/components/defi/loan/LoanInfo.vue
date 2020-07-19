<template>
  <v-row v-if="!!loan" class="loan-info">
    <v-col cols="12">
      <loan-header :loan="loan" />
      <v-row>
        <v-col cols="12" md="6">
          <loan-collateral :loan="loan" />
          <loan-debt v-if="isVault" :loan="loan" class="mt-5" />
        </v-col>
        <v-col cols="12" md="6">
          <loan-debt v-if="!isVault" :loan="loan" />
          <loan-liquidation v-if="isVault" :loan="loan" />
        </v-col>
      </v-row>
      <v-row v-if="isVault" class="mt-6">
        <v-col cols="12">
          <premium-card
            v-if="!premium"
            title="Borrowing History"
          ></premium-card>
          <vault-events-list
            v-else
            :asset="loan.collateral.asset"
            :events="loan.events"
            :creation="loan.creationTs"
            @open-link="openLink($event)"
          ></vault-events-list>
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import LoanDisplayMixin from '@/components/defi/loan/loan-display-mixin';
import LoanCollateral from '@/components/defi/loan/LoanCollateral.vue';
import LoanDebt from '@/components/defi/loan/LoanDebt.vue';
import LoanHeader from '@/components/defi/loan/LoanHeader.vue';
import LoanLiquidation from '@/components/defi/loan/LoanLiquidation.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import PremiumCard from '@/components/display/PremiumCard.vue';
import StatCard from '@/components/display/StatCard.vue';
import HashLink from '@/components/helper/HashLink.vue';
import PremiumLock from '@/components/helper/PremiumLock.vue';
import PremiumMixin from '@/mixins/premium-mixin';
import { VaultEventsList } from '@/utils/premium';

@Component({
  components: {
    LoanCollateral,
    LoanDebt,
    LoanHeader,
    LoanLiquidation,
    BaseExternalLink,
    PremiumCard,
    PremiumLock,
    HashLink,
    AmountDisplay,
    StatCard,
    VaultEventsList
  },
  computed: {
    ...mapGetters('session', ['dateDisplayFormat'])
  }
})
export default class LoanInfo extends Mixins(PremiumMixin, LoanDisplayMixin) {
  dateDisplayFormat!: string;

  openLink(url: string) {
    this.$interop.openUrl(url);
  }
}
</script>
