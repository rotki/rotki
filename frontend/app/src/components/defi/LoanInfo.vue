<template>
  <v-row v-if="!!vault" class="loan-info">
    <v-col cols="12">
      <v-row>
        <v-col class="loan-info__header">
          <div class="loan-info__header__identifier">
            Maker Vault #{{ vault.identifier }} ({{ vault.collateralType }})
          </div>
          <div class="loan-info__header__owner secondary--text text--lighten-2">
            Owned by:
            <hash-link
              :text="vault.owner"
              class="d-inline font-weight-medium"
            ></hash-link>
          </div>
        </v-col>
      </v-row>
      <v-row>
        <v-col cols="12" md="6">
          <stat-card title="Collateral">
            <div class="d-flex justify-space-between font-weight-medium">
              <div>
                Locked up collateral
              </div>
              <div>
                <amount-display
                  :value="vault.collateralAmount"
                  :asset="vault.collateralAsset"
                ></amount-display>
              </div>
            </div>
            <div class="text-right">
              <div>
                <amount-display
                  :value="vault.collateralUsdValue"
                  fiat-currency="USD"
                  show-currency="ticker"
                ></amount-display>
              </div>
            </div>
            <v-divider class="my-4"></v-divider>
            <div class="d-flex justify-space-between mb-2 font-weight-medium">
              <div>
                Current ratio
              </div>
              <div>
                {{
                  vault.collateralizationRatio
                    ? vault.collateralizationRatio
                    : '-'
                }}
              </div>
            </div>
            <v-btn
              small
              rounded
              block
              depressed
              color="grey lighten-3 grey--text text--darken-2"
              class="loan-info__watcher-button"
              @click="premium ? openWatcherDialog(vault) : ''"
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
          </stat-card>
          <stat-card class="loan-info__debt mt-5" title="Debt">
            <div class="d-flex justify-space-between font-weight-medium">
              <div>
                Outstanding debt
              </div>
              <div>
                <amount-display
                  :value="vault.debtValue"
                  asset="DAI"
                ></amount-display>
              </div>
            </div>
            <v-divider class="my-4"></v-divider>
            <div
              class="loan-info__debt__stability-fee d-flex justify-space-between mb-2 font-weight-medium"
            >
              <div>
                Stability fee
              </div>
              <div>
                {{ vault.stabilityFee }}
              </div>
            </div>
            <div class="d-flex justify-space-between font-weight-medium">
              <div>
                Total interest owed
              </div>
              <div v-if="premium">
                <amount-display
                  v-if="
                    vault.totalInterestOwed &&
                    !vault.totalInterestOwed.isNegative()
                  "
                  :value="vault.totalInterestOwed"
                  asset="DAI"
                ></amount-display>
                <amount-display
                  v-else
                  :loading="vault.totalInterestOwed === undefined"
                  :value="'0.00'"
                  asset="DAI"
                ></amount-display>
              </div>
              <div v-else>
                <premium-lock></premium-lock>
              </div>
            </div>
          </stat-card>
        </v-col>
        <v-col cols="12" md="6">
          <stat-card title="Liquidation" class="loan-info__liquidation">
            <div class="loan-info__liquidation__upper pb-5">
              <div class="d-flex justify-space-between font-weight-medium">
                <div>
                  Liquidation price
                </div>
                <div>
                  <amount-display
                    fiat-currency="USD"
                    show-currency="ticker"
                    :value="vault.liquidationPrice"
                  ></amount-display>
                </div>
              </div>
              <v-divider class="my-4"></v-divider>
              <div class="d-flex justify-space-between">
                <div>
                  Minimum ratio
                </div>
                <div>
                  {{ vault.liquidationRatio }}
                </div>
              </div>
            </div>
            <div>
              <span class="loan-info__liquidation__liquidation-events__header">
                Liquidation Events
              </span>
              <v-skeleton-loader
                v-if="premium"
                :loading="typeof vault.totalLiquidatedAmount === 'undefined'"
                class="mx-auto pt-3"
                max-width="450"
                type="paragraph"
              >
                <div
                  v-if="
                    vault.totalLiquidatedAmount &&
                    vault.totalLiquidatedAmount.gt(0)
                  "
                  class="loan-info__liquidation-events__content"
                >
                  <div
                    class="loan-info__liquidation-events__content__liquidated-collateral mb-2"
                  >
                    <div
                      class="d-flex justify-space-between font-weight-medium"
                    >
                      <div>
                        Liquidated collateral
                      </div>
                      <div>
                        <amount-display
                          :value="vault.totalLiquidatedAmount"
                          :asset="vault.collateralAsset"
                        ></amount-display>
                      </div>
                    </div>
                    <div class="d-flex justify-end">
                      <div>
                        <amount-display
                          :value="vault.totalLiquidatedUsd"
                          show-currency="ticker"
                          fiat-currency="USD"
                        ></amount-display>
                      </div>
                    </div>
                  </div>
                  <div class="d-flex justify-space-between font-weight-medium">
                    <div>
                      Outstanding debt at liquidation
                    </div>
                    <div>
                      <amount-display
                        :value="vault.totalInterestOwed"
                        asset="DAI"
                      ></amount-display>
                    </div>
                  </div>
                  <v-divider class="my-4"></v-divider>
                  <div class="d-flex justify-space-between font-weight-medium">
                    <div>
                      Total value lost
                    </div>
                    <div>
                      <amount-display
                        :value="
                          vault.totalLiquidatedUsd.plus(vault.totalInterestOwed)
                        "
                        show-currency="ticker"
                        fiat-currency="USD"
                      ></amount-display>
                    </div>
                  </div>
                </div>
                <div v-else>
                  No liquidation events have occurred for this loan.
                </div>
              </v-skeleton-loader>
              <div v-else class="text-right">
                <premium-lock></premium-lock>
              </div>
            </div>
          </stat-card>
        </v-col>
      </v-row>
      <v-row class="mt-6">
        <v-col cols="12">
          <premium-card
            v-if="!premium"
            title="Borrowing History"
          ></premium-card>
          <vault-events-list
            v-else
            :asset="vault.collateralAsset"
            :events="vault.events"
            :creation="vault.creationTs"
            @open-link="openLink($event)"
          ></vault-events-list>
        </v-col>
      </v-row>
    </v-col>
    <watcher-dialog
      :display="showWatcherDialog"
      title="Collateralization watchers"
      :message="watcherMessage"
      :watcher-content-id="watcherVaultId"
      :existing-watchers="watchers"
      preselect-watcher-type="makervault_collateralization_ratio"
      watcher-value-label="Collateralization Ratio"
      @cancel="showWatcherDialog = false"
    >
    </watcher-dialog>
  </v-row>
  <v-row v-else align="center" justify="center">
    <v-col>
      <span class="font-weight-light text-subtitle-2">
        Please select a loan to see information
      </span>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { mapGetters, mapState } from 'vuex';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import WatcherDialog from '@/components/dialogs/WatcherDialog.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import PremiumCard from '@/components/display/PremiumCard.vue';
import StatCard from '@/components/display/StatCard.vue';
import HashLink from '@/components/helper/HashLink.vue';
import PremiumLock from '@/components/helper/PremiumLock.vue';
import { Watcher, WatcherType } from '@/services/defi/types';
import { MakerDAOVault, MakerDAOVaultModel } from '@/store/defi/types';
import { VaultEventsList } from '@/utils/premium';

@Component({
  components: {
    BaseExternalLink,
    PremiumCard,
    PremiumLock,
    HashLink,
    AmountDisplay,
    StatCard,
    VaultEventsList,
    WatcherDialog
  },
  computed: {
    ...mapState('session', ['premium']),
    ...mapGetters('session', ['dateDisplayFormat']),
    ...mapGetters('defi', ['loanWatchers'])
  }
})
export default class LoanInfo extends Vue {
  @Prop({ required: true })
  vault!: MakerDAOVault | MakerDAOVaultModel | null;

  premium!: boolean;
  dateDisplayFormat!: string;
  showWatcherDialog: boolean = false;
  watcherMessage: string = '';
  watcherVaultId: number | null = null;
  loanWatchers!: Watcher<WatcherType>[];

  get watchers(): Watcher<WatcherType>[] {
    if (!this.vault) {
      return [];
    }
    return this.loanWatchers.filter(watcher => {
      const watcherArgs = watcher.args;

      if (watcherArgs.vault_id.indexOf(String(this.vault!.identifier)) > -1)
        return watcher;
    });
  }

  openWatcherDialog(vault: MakerDAOVault) {
    this.showWatcherDialog = true;
    this.watcherVaultId = vault.identifier;
    this.watcherMessage = `Add / Edit / Delete watchers for Maker Vault #${vault.identifier} with current collateralization ratio ${vault.collateralizationRatio} and liquidation ratio ${vault.liquidationRatio}.`;
  }

  openLink(url: string) {
    this.$interop.openUrl(url);
  }
}
</script>

<style scoped lang="scss">
.loan-info {
  &__header {
    &__identifier {
      font-size: 24px;
      font-weight: bold;
    }
  }

  &__collateral {
    &__watcher {
      border-radius: 15px;
    }
  }

  &__watcher-button {
    text-transform: none;
  }

  &__liquidation {
    height: 100%;
    display: flex;
    flex-direction: column;

    &__upper {
      min-height: 100px;
      height: 45%;
    }

    ::v-deep {
      .v-card {
        &__text {
          display: flex;
          flex-direction: column;
        }
      }
    }

    &__liquidation-events {
      &__header {
        font-size: 20px;
        font-weight: 500;
        color: rgba(0, 0, 0, 0.87);
      }
    }
  }
}
</style>
