<template>
  <v-container id="settings-account">
    <v-row>
      <v-col>
        <h1 class="page-header">Accounting Settings</h1>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <v-card>
          <v-card-title>Trade Settings</v-card-title>
          <v-card-text>
            <v-switch
              v-model="crypto2CryptoTrades"
              class="settings-accounting__crypto2crypto"
              label="Take into account crypto to crypto trades"
              color="primary"
              @change="onCrypto2CryptoChange($event)"
            ></v-switch>
            <v-switch
              v-model="gasCosts"
              class="settings-accounting__include-gas-costs"
              label="Take into account Ethereum gas costs"
              color="primary"
              @change="onGasCostChange($event)"
            ></v-switch>
            <v-switch
              v-model="taxFreePeriod"
              class="settings-accounting__taxfree-period"
              label="Is there a tax free period?"
              color="primary"
              @change="onTaxFreeChange($event)"
            ></v-switch>
            <v-text-field
              v-model="taxFreeAfterPeriod"
              class="settings-accounting__taxfree-period-days"
              :disabled="!taxFreePeriod"
              :rules="taxFreeRules"
              label="Tax free after how many days"
              type="number"
            >
            </v-text-field>
          </v-card-text>
          <v-card-actions>
            <v-btn
              class="settings-accounting__modify-trade-settings"
              depressed
              color="primary"
              type="submit"
              @click="modifyTradeSettings()"
            >
              Set
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <v-card>
          <v-card-title>Asset Settings</v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="10">
                <v-text-field
                  v-model="assetToIgnore"
                  class="settings-accounting__asset"
                  label="Asset To Ignore"
                  @keyup.enter="addAsset()"
                ></v-text-field>
              </v-col>
              <v-col cols="2">
                <v-btn
                  class="settings-accounting__buttons__add"
                  text
                  color="primary"
                  :disabled="assetToIgnore === ''"
                  @click="addAsset()"
                >
                  Add
                </v-btn>
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="10">
                <v-select
                  v-model="assetToRemove"
                  class="settings-accounting__ignored-assets"
                  :items="ignoredAssets"
                  hint="Click to see all ignored assets and select one for removal"
                  label="Ignored Assets"
                >
                  <div slot="append-outer">
                    <v-badge>
                      <template #badge>
                        <span
                          class="settings-accounting__ignored-assets__badge"
                        >
                          {{ ignoredAssets.length }}
                        </span>
                      </template>
                    </v-badge>
                  </div>
                </v-select>
              </v-col>
              <v-col cols="2">
                <v-btn
                  class="settings-accounting__buttons__remove"
                  text
                  color="primary"
                  :disabled="assetToRemove === ''"
                  @click="removeAsset()"
                >
                  Remove
                </v-btn>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import { Message } from '@/store/store';
import { AccountingSettings } from '@/typing/types';

const { mapState } = createNamespacedHelpers('session');

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

  ignoredAssets: string[] = [];
  assetToIgnore: string = '';
  assetToRemove: string = '';

  taxFreeRules = [
    (v: string) => !!v || 'Please enter the number of days',
    (v: string) =>
      (v && parseInt(v) > 0) || 'The number of days cannot negative or zero'
  ];

  created() {
    this.$api
      .ignoredAssets()
      .then(assets => {
        this.ignoredAssets = assets;
      })
      .catch(() => {
        this.$store.commit('setMessage', {
          title: 'Error',
          description: 'Failed to retrieve the ignored assets'
        } as Message);
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
    } else {
      period = -1;
    }

    const { commit } = this.$store;

    this.$api
      .setSettings({ taxfree_after_period: period })
      .then(settings => {
        commit('setMessage', {
          title: 'Success',
          description: 'Successfully set trade settings',
          success: true
        } as Message);

        commit('session/accountingSettings', {
          ...this.accountingSettings,
          taxFreeAfterPeriod: settings.taxfree_after_period
        });
      })
      .catch((reason: Error) => {
        commit('setMessage', {
          title: 'Error setting trade settings',
          description: reason.message
        } as Message);
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
    const { commit } = this.$store;
    this.$api
      .setSettings({ include_crypto2crypto: enabled })
      .then(settings => {
        commit('setMessage', {
          title: 'Success',
          description: 'Successfully set crypto to crypto consideration value',
          success: true
        } as Message);
        commit('session/accountingSettings', {
          ...this.accountingSettings,
          includeCrypto2Crypto: settings.include_crypto2crypto
        });
      })
      .catch(reason => {
        commit('setMessage', {
          title: 'Error',
          description: `Error setting crypto to crypto ${reason.message}`
        } as Message);
      });
  }

  onGasCostChange(enabled: boolean) {
    const { commit } = this.$store;

    this.$api
      .setSettings({ include_gas_costs: enabled })
      .then(settings => {
        commit('setMessage', {
          title: 'Success',
          description: 'Successfully set Ethereum gas costs value',
          success: true
        } as Message);
        commit('session/accountingSettings', {
          ...this.accountingSettings,
          includeGasCosts: settings.include_gas_costs
        });
      })
      .catch(reason => {
        commit('setMessage', {
          title: 'Error',
          description: `Error setting Ethereum gas costs: ${reason.message}`
        } as Message);
      });
  }

  addAsset() {
    const { commit } = this.$store;

    this.$api
      .modifyAsset(true, this.assetToIgnore)
      .then(ignoredAssets => {
        this.ignoredAssets = ignoredAssets;
        this.assetToIgnore = '';
      })
      .catch((reason: Error) => {
        commit('setMessage', {
          title: 'Ignored Asset Modification Error',
          description: `Error at modifying ignored asset ${this.assetToIgnore} (${reason.message})`
        } as Message);
      });
  }

  removeAsset() {
    this.$api
      .modifyAsset(false, this.assetToRemove)
      .then(ignoredAssets => {
        this.ignoredAssets = ignoredAssets;
        this.assetToRemove = '';
      })
      .catch((reason: Error) => {
        const { commit } = this.$store;

        commit('setMessage', {
          title: 'Ignored Asset Modification Error',
          description: `Error at modifying ignored asset ${this.assetToIgnore} (${reason.message})`
        } as Message);
      });
  }
}
</script>

<style scoped></style>
