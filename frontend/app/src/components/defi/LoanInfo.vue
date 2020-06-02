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
            <base-external-link
              truncate
              :text="vault.owner"
              :href="`https://etherscan.io/address/${vault.owner}`"
            >
            </base-external-link>
          </div>
        </v-col>
      </v-row>
      <v-row>
        <v-col cols="12" md="6">
          <stat-card title="Collateral">
            <div class="d-flex justify-space-between">
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
              <div class="font-weight-light">
                <amount-display
                  :value="vault.collateralUsdValue"
                  fiat-currency="USD"
                  show-currency="ticker"
                ></amount-display>
              </div>
            </div>
            <v-divider class="my-4"></v-divider>
            <div class="d-flex justify-space-between mb-2">
              <div>
                Current ratio
              </div>
              <div>
                {{
                  vault.collateralizationRatio
                    ? vault.collateralizationRatio
                    : 'NaN'
                }}
              </div>
            </div>
            <v-btn
              x-small
              rounded
              block
              depressed
              color="grey lighten-3 grey--text text--darken-2"
              @click="premium ? openWatcherDialog(vault) : ''"
            >
              <v-icon x-small left>fa fa-bell-o</v-icon>
              <span style="text-transform: none;" class="caption">
                Add a collateralization ratio watcher
              </span>
              <premium-lock v-if="!premium" size="x-small"></premium-lock>
            </v-btn>
          </stat-card>
          <stat-card class="loan-info__debt mt-5" title="Debt">
            <div class="d-flex justify-space-between">
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
            <div class="text-right">
              <div class="font-weight-light">
                xx.xx XYZ
              </div>
            </div>
            <v-divider class="my-4"></v-divider>
            <div
              class="loan-info__debt__stability-fee d-flex justify-space-between mb-2"
            >
              <div>
                Stability fee
              </div>
              <div>
                {{ vault.stabilityFee }}
              </div>
            </div>
            <div class="d-flex justify-space-between">
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
                  :loading="typeof vault.totalInterestOwed === 'undefined'"
                  :value="'0.00'"
                  asset="DAI"
                ></amount-display>
              </div>
              <div v-else>
                <premium-lock></premium-lock>
              </div>
            </div>
            <div v-if="premium" class="text-right">
              <div class="font-weight-light">
                xx.xx XYZ
              </div>
            </div>
          </stat-card>
        </v-col>
        <v-col cols="12" md="6">
          <stat-card title="Liquidation" class="loan-info__liquidation">
            <div class="loan-info__liquidation__upper pb-5">
              <div class="d-flex justify-space-between">
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
              <div class="d-flex justify-space-between font-weight-light">
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
                    <div class="d-flex justify-space-between">
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
                    <div class="d-flex justify-end font-weight-light">
                      <div>
                        <amount-display
                          :value="vault.totalLiquidatedUsd"
                          show-currency="ticker"
                          fiat-currency="USD"
                        ></amount-display>
                      </div>
                    </div>
                  </div>
                  <div class="d-flex justify-space-between">
                    <div>
                      Outsanding debt at liquidation
                    </div>
                    <div>
                      <amount-display
                        :value="vault.totalInterestOwed"
                        asset="DAI"
                      ></amount-display>
                    </div>
                  </div>
                  <v-divider class="my-4"></v-divider>
                  <div class="d-flex justify-space-between">
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
      <v-row>
        <v-col cols="12">
          <premium-card v-if="!premium" title="Loan History"></premium-card>
          <vault-events-list
            v-else
            :asset="vault.collateralAsset"
            :events="vault.events"
            :creation="vault.creationTs"
            @open-transaction="openTransaction($event)"
          ></vault-events-list>
        </v-col>
      </v-row>
    </v-col>
    <watcher-dialog
      :display="showWatcherDialog"
      title="Add loan collateralization watcher"
      :message="watcherMessage"
      :watcher-content-id="watcherVaultId"
      preselect-watcher-type="makervault_collateralization_ratio"
      watcher-value-label="Collateralization Ratio"
      @confirm="addWatcher()"
      @cancel="showWatcherDialog = false"
    >
    </watcher-dialog>
  </v-row>
  <v-row v-else align="center" justify="center">
    <v-col>
      <span class="font-weight-light subtitle-2">
        Please select a loan to see information
      </span>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import WatcherDialog from '@/components/dialogs/WatcherDialog.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import PremiumCard from '@/components/display/PremiumCard.vue';
import StatCard from '@/components/display/StatCard.vue';
import PremiumLock from '@/components/helper/PremiumLock.vue';
import { MakerDAOVault } from '@/services/types-model';
import { MakerDAOVaultModel } from '@/store/balances/types';
import { VaultEventsList } from '@/utils/premium';

const { mapState, mapGetters } = createNamespacedHelpers('session');

@Component({
  components: {
    BaseExternalLink,
    PremiumCard,
    PremiumLock,
    AmountDisplay,
    StatCard,
    VaultEventsList,
    WatcherDialog
  },
  computed: {
    ...mapState(['premium']),
    ...mapGetters(['dateDisplayFormat'])
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

  openWatcherDialog(vault: MakerDAOVault) {
    this.showWatcherDialog = true;
    this.watcherVaultId = vault.identifier;
    this.watcherMessage = `Please fill in the details for the watcher you would like to add for Maker Vault #${vault.identifier} with current collateralization ratio ${vault.collateralizationRatio} and liquidation ratio ${vault.liquidationRatio}.`;
  }

  openTransaction(url: string) {
    this.$interop.openUrl(url);
  }

  addWatcher() {
    this.showWatcherDialog = false;
    window.alert('api thing in WatcherDialog');
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

  &__liquidation {
    height: 100%;
    display: flex;
    flex-direction: column;

    &__upper {
      min-height: 100px;
      height: 45%;
    }

    ::v-deep .v-card__text {
      display: flex;
      flex-direction: column;
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
