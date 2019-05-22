<template xmlns:v-slot="http://www.w3.org/1999/XSL/Transform">
  <v-container id="settings-account">
    <v-layout>
      <v-flex>
        <h1 class="page-header">Accounting Settings</h1>
      </v-flex>
    </v-layout>
    <v-layout>
      <v-flex>
        <v-card>
          <v-toolbar card>Trade Settings</v-toolbar>
          <v-card-text>
            <v-switch
              id="crypto2crypto"
              v-model="crypto2CryptoTrades"
              label="Take into account crypto to crypto trades"
              color="primary"
              @change="onCrypto2CryptoChange($event)"
            ></v-switch>
            <v-switch
              id="include_gas_costs"
              v-model="gasCosts"
              label="Take into account Ethereum gas costs"
              color="primary"
              @change="onGasCostChange($event)"
            ></v-switch>
            <v-switch
              id="taxfree_period_exists"
              v-model="taxFreePeriod"
              label="Is there a tax free period?"
              color="primary"
              @change="onTaxFreeChange($event)"
            ></v-switch>
            <v-text-field
              v-model="taxFreeAfterPeriod"
              :disabled="!taxFreePeriod"
              label="Tax free after how many days"
              type="number"
            >
            </v-text-field>
          </v-card-text>
          <v-card-actions>
            <v-btn
              id="modify_trade_settings"
              depressed
              type="submit"
              @click="modifyTradeSettings()"
            >
              Set
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-flex>
    </v-layout>
    <v-layout>
      <v-flex>
        <v-card>
          <v-toolbar card>Asset Settings</v-toolbar>
          <v-card-text>
            <v-layout>
              <v-flex xs10>
                <v-text-field
                  v-model="assetToIgnore"
                  label="Asset To Ignore"
                  @keyup.enter="addAsset()"
                ></v-text-field>
              </v-flex>
              <v-flex xs2>
                <v-btn
                  flat
                  color="primary"
                  :disabled="assetToIgnore === ''"
                  @click="addAsset()"
                >
                  Add
                </v-btn>
              </v-flex>
            </v-layout>
            <v-layout>
              <v-flex xs10>
                <v-select
                  v-model="assetToRemove"
                  :items="ignoredAssets"
                  hint="Click to see all ignored assets and select one for removal"
                  label="Ignored Assets"
                >
                  <div slot="append-outer">
                    <v-badge>
                      <template v-slot:badge>
                        <span>{{ ignoredAssets.length }}</span>
                      </template>
                    </v-badge>
                  </div>
                </v-select>
              </v-flex>
              <v-flex xs2>
                <v-btn
                  flat
                  color="primary"
                  :disabled="assetToRemove === ''"
                  @click="removeAsset()"
                >
                  Remove
                </v-btn>
              </v-flex>
            </v-layout>
          </v-card-text>
        </v-card>
      </v-flex>
    </v-layout>
    <message-dialog
      :success="true"
      title="Success"
      :message="successMessage"
      @dismiss="dismiss()"
    ></message-dialog>
    <message-dialog
      :title="errorTitle"
      :message="errorMessage"
      @dismiss="dismiss()"
    ></message-dialog>
    <div id="settings-accounting"></div>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapState } from 'vuex';
import { AccountingSettings } from '@/typing/types';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';

@Component({
  components: {
    MessageDialog
  },
  computed: mapState(['accountingSettings'])
})
export default class Accounting extends Vue {
  accountingSettings!: AccountingSettings;

  crypto2CryptoTrades: boolean = false;
  gasCosts: boolean = false;
  taxFreeAfterPeriod: number | null = null;
  taxFreePeriod: boolean = false;

  successMessage: string = '';
  errorMessage: string = '';
  errorTitle: string = '';

  ignoredAssets: string[] = [];
  assetToIgnore: string = '';
  assetToRemove: string = '';

  dismiss() {
    this.errorMessage = '';
    this.successMessage = '';
    this.errorTitle = '';
  }

  created() {
    this.$rpc
      .get_ignored_assets()
      .then(assets => {
        this.ignoredAssets = assets;
      })
      .catch(() => {
        this.errorTitle = 'Error';
        this.errorMessage = 'Failed to retrieve the ignored assets';
      });
  }

  mounted() {
    this.crypto2CryptoTrades = this.accountingSettings.includeCrypto2Crypto;
    this.gasCosts = this.accountingSettings.includeGasCosts;
    if (this.accountingSettings.taxFreeAfterPeriod) {
      this.taxFreePeriod = true;
      this.taxFreeAfterPeriod =
        this.accountingSettings.taxFreeAfterPeriod / 86400;
    } else {
      this.taxFreePeriod = false;
      this.taxFreeAfterPeriod = null;
    }
  }

  modifyTradeSettings() {
    let period = this.taxFreeAfterPeriod;
    if (period !== null) {
      period *= 86400;
    }

    this.$rpc
      .set_settings({ taxfree_after_period: period })
      .then(() => {
        this.successMessage = 'Successfully set trade settings';
        this.$store.commit(
          'accountingSettings',
          Object.assign({}, this.accountingSettings, {
            taxFreeAfterPeriod: period
          })
        );
      })
      .catch((reason: Error) => {
        this.errorTitle = 'Error setting trade settings';
        this.errorMessage = reason.message;
      });
  }

  onTaxFreeChange(enabled: boolean) {
    if (!enabled) {
      this.taxFreeAfterPeriod = null;
    } else {
      const period = this.accountingSettings.taxFreeAfterPeriod;
      if (period) {
        this.taxFreeAfterPeriod = period / 86400;
      } else {
        this.taxFreeAfterPeriod = 0;
      }
    }
  }

  onCrypto2CryptoChange(enabled: boolean) {
    this.$rpc
      .set_settings({ include_crypto2crypto: enabled })
      .then(() => {
        this.successMessage =
          'Successfully set crypto to crypto consideration value';
        this.$store.commit(
          'accountingSettings',
          Object.assign({}, this.accountingSettings, {
            includeCrypto2Crypto: enabled
          })
        );
      })
      .catch(reason => {
        this.errorTitle = 'Error';
        this.errorMessage = `Error setting crypto to crypto ${reason.message}`;
      });
  }

  onGasCostChange(enabled: boolean) {
    this.$rpc
      .set_settings({ include_gas_costs: enabled })
      .then(() => {
        this.successMessage = 'Successfully set Ethereum gas costs value';
        this.$store.commit(
          'accountingSettings',
          Object.assign({}, this.accountingSettings, {
            includeGasCosts: enabled
          })
        );
      })
      .catch(reason => {
        this.errorTitle = 'Error';
        this.errorMessage = `Error setting Ethereum gas costs: ${reason.message}`;
      });
  }

  addAsset() {
    this.$rpc
      .modify_asset(true, this.assetToIgnore)
      .then(() => {
        this.ignoredAssets.push(this.assetToIgnore);
        this.assetToIgnore = '';
      })
      .catch((reason: Error) => {
        this.errorTitle = 'Ignored Asset Modification Error';
        this.errorMessage = `Error at modifying ignored asset ${this.assetToIgnore} (${reason.message})`;
      });
  }

  removeAsset() {
    this.$rpc
      .modify_asset(false, this.assetToRemove)
      .then(() => {
        const index = this.ignoredAssets.findIndex(
          value => value == this.assetToRemove
        );
        if (index >= 0) {
          this.ignoredAssets.splice(index, 1);
        }
        this.assetToRemove = '';
      })
      .catch((reason: Error) => {
        this.errorTitle = 'Ignored Asset Modification Error';
        this.errorMessage = `Error at modifying ignored asset ${this.assetToIgnore} (${reason.message})`;
      });
  }
}
</script>

<style scoped></style>
