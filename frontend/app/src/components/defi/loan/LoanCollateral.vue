<template>
  <stat-card title="Collateral">
    <loan-row v-if="isVault" title="Locked up collateral">
      <amount-display
        :value="loan.collateral.amount"
        :asset="loan.collateral.asset"
      />
    </loan-row>
    <loan-row :medium="!isVault" :title="isVault ? '' : 'Locked up collateral'">
      <amount-display
        :value="loan.collateral.usdValue"
        fiat-currency="USD"
        show-currency="ticker"
      />
    </loan-row>
    <v-divider class="my-4" />
    <loan-row v-if="isVault" title="Current ratio" class="mb-2">
      {{ loan.collateralizationRatio | optional }}
    </loan-row>
    <loan-row v-if="!isVault" title="Stable APR" class="mb-2">
      {{ loan.stableApr | optional }}
    </loan-row>
    <loan-row v-if="!isVault" title="Variable APR">
      {{ loan.variableApr | optional }}
    </loan-row>
    <v-btn
      v-if="isVault"
      small
      rounded
      block
      depressed
      color="grey lighten-3 grey--text text--darken-2"
      class="loan-collateral__watcher-button"
      @click="openWatcherDialog"
    >
      <v-icon x-small left>fa fa-bell-o</v-icon>
      <span v-if="watchers.length > 0" class="text-caption">
        Edit {{ watchers.length }} collateralization watcher(s)
      </span>
      <span v-else class="text-caption">
        Add collateralization ratio watcher
      </span>
      <premium-lock v-if="!premium" size="x-small"></premium-lock>
    </v-btn>
    <watcher-dialog
      v-if="isVault"
      :display="showWatcherDialog"
      title="Collateralization watchers"
      :message="watcherMessage"
      :watcher-content-id="watcherVaultId"
      :existing-watchers="watchers"
      preselect-watcher-type="makervault_collateralization_ratio"
      watcher-value-label="Collateralization Ratio"
      @cancel="showWatcherDialog = false"
    />
  </stat-card>
</template>
<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import LoanDisplayMixin from '@/components/defi/loan/loan-display-mixin';
import LoanRow from '@/components/defi/loan/LoanRow.vue';
import WatcherDialog from '@/components/dialogs/WatcherDialog.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import StatCard from '@/components/display/StatCard.vue';
import PremiumLock from '@/components/helper/PremiumLock.vue';
import PremiumMixin from '@/mixins/premium-mixin';
import { Watcher, WatcherType } from '@/services/session/types';
import { MakerDAOVaultModel } from '@/store/defi/types';

@Component({
  components: { WatcherDialog, LoanRow, AmountDisplay, PremiumLock, StatCard },
  computed: {
    ...mapGetters('session', ['loanWatchers'])
  }
})
export default class LoanCollateral extends Mixins(
  PremiumMixin,
  LoanDisplayMixin
) {
  showWatcherDialog: boolean = false;
  watcherMessage: string = '';
  watcherVaultId: string | null = null;
  loanWatchers!: Watcher<WatcherType>[];

  get watchers(): Watcher<WatcherType>[] {
    if (!this.loan) {
      return [];
    }
    return this.loanWatchers.filter(watcher => {
      const watcherArgs = watcher.args;

      if (watcherArgs.vault_id.indexOf(this.loan!.identifier) > -1)
        return watcher;
    });
  }

  openWatcherDialog() {
    if (!this.premium || !this.isVault) {
      return;
    }
    const { collateralizationRatio, identifier, liquidationRatio } = this
      .loan as MakerDAOVaultModel;
    this.showWatcherDialog = true;
    this.watcherVaultId = identifier;
    this.watcherMessage = `Add / Edit / Delete watchers for Maker Vault #${identifier} with current collateralization ratio ${collateralizationRatio} and liquidation ratio ${liquidationRatio}.`;
  }
}
</script>

<style scoped lang="scss">
.loan-collateral {
  &__watcher {
    border-radius: 15px;
  }

  &__watcher-button {
    text-transform: none;
  }
}
</style>
