<template>
  <stat-card :title="$t('loan_collateral.title')">
    <loan-row v-if="isVault" :title="$t('loan_collateral.locked_collateral')">
      <amount-display
        :asset-padding="assetPadding"
        :value="loan.collateral.amount"
        :asset="loan.collateral.asset"
      />
    </loan-row>
    <loan-row
      :medium="!isVault"
      :title="isVault ? '' : $t('loan_collateral.locked_collateral')"
    >
      <amount-display
        :asset-padding="assetPadding"
        :value="isVault ? loan.collateral.usdValue : totalCollateralUsd"
        fiat-currency="USD"
      />
    </loan-row>
    <v-divider class="my-4" />
    <loan-row
      v-if="(isAave || isCompound) && loan.collateral.length > 0"
      :title="$t('loan_collateral.per_asset')"
    >
      <div class="loan-collateral__collateral" />
      <v-row
        v-for="collateral in loan.collateral"
        :key="collateral.asset"
        no-gutters
      >
        <v-col>
          <balance-display
            :asset="collateral.asset"
            :value="collateral"
            :min-width="18"
          />
        </v-col>
      </v-row>
    </loan-row>
    <v-divider
      v-if="(isAave || isCompound) && loan.collateral.length > 0"
      class="my-4"
    />
    <loan-row
      v-if="isVault"
      :title="$t('loan_collateral.current_ratio')"
      class="mb-2"
    >
      <percentage-display
        :value="
          loan.collateralizationRatio ? loan.collateralizationRatio : null
        "
      />
    </loan-row>
    <loan-row
      v-if="isAave"
      :title="$t('loan_collateral.stable_apr')"
      class="mb-2"
    >
      <percentage-display :value="loan.stableApr ? loan.stableApr : null" />
    </loan-row>
    <loan-row v-if="isAave" :title="$t('loan_collateral.variable_apr')">
      <percentage-display :value="loan.variableApr ? loan.variableApr : null" />
    </loan-row>
    <loan-row v-if="isCompound" :title="$t('loan_collateral.apy')">
      <percentage-display :value="loan.apy ? loan.apy : null" />
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
      <v-icon x-small left>mdi-bell-outline</v-icon>
      <span v-if="watchers.length > 0" class="text-caption">
        {{
          $tc('loan_collateral.watchers.edit', watchers.length, {
            n: watchers.length
          })
        }}
      </span>
      <span v-else class="text-caption">
        {{ $t('loan_collateral.watchers.add') }}
      </span>
      <premium-lock v-if="!premium" size="x-small" />
    </v-btn>
    <watcher-dialog
      v-if="isVault"
      :display="showWatcherDialog"
      :title="$t('loan_collateral.watchers.dialog.title')"
      :message="watcherMessage"
      :watcher-content-id="watcherVaultId"
      :existing-watchers="watchers"
      preselect-watcher-type="makervault_collateralization_ratio"
      :watcher-value-label="$t('loan_collateral.watchers.dialog.label')"
      @cancel="showWatcherDialog = false"
    />
  </stat-card>
</template>
<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import { Component, Mixins } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import LoanDisplayMixin from '@/components/defi/loan/loan-display-mixin';
import LoanRow from '@/components/defi/loan/LoanRow.vue';
import WatcherDialog from '@/components/dialogs/WatcherDialog.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import StatCard from '@/components/display/StatCard.vue';
import PremiumLock from '@/components/helper/PremiumLock.vue';
import PremiumMixin from '@/mixins/premium-mixin';
import { Watcher, WatcherType } from '@/services/session/types';
import { Collateral, MakerDAOVaultModel } from '@/store/defi/types';
import { Zero } from '@/utils/bignumbers';

@Component({
  components: {
    PercentageDisplay,
    WatcherDialog,
    LoanRow,
    AmountDisplay,
    PremiumLock,
    StatCard
  },
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

  get totalCollateralUsd(): BigNumber {
    return this.loan
      ? (this.loan.collateral as Collateral<string>[])
          .map(({ usdValue }) => usdValue)
          .reduce((sum, value) => sum.plus(value), Zero)
      : Zero;
  }

  readonly assetPadding: number = 5;

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

    const params = {
      collateralizationRatio,
      identifier,
      liquidationRatio
    };
    this.showWatcherDialog = true;
    this.watcherVaultId = identifier;
    this.watcherMessage = this.$t(
      'loan_collateral.watchers.dialog.message',
      params
    ).toString();
  }
}
</script>

<style scoped lang="scss">
@import '~@/scss/scroll';

.loan-collateral {
  &__watcher {
    border-radius: 15px;
  }

  &__collateral {
    max-height: 200px;
    overflow-y: scroll;

    @extend .themed-scrollbar;
  }

  &__watcher-button {
    text-transform: none;
  }
}
</style>
