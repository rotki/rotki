<template>
  <v-container id="settings-account">
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
              :success-messages="settingsMessages['crypto2crypto'].success"
              :error-messages="settingsMessages['crypto2crypto'].error"
              @change="onCrypto2CryptoChange($event)"
            ></v-switch>
            <v-switch
              v-model="gasCosts"
              class="settings-accounting__include-gas-costs"
              label="Take into account Ethereum gas costs"
              :success-messages="settingsMessages['gasCostChange'].success"
              :error-messages="settingsMessages['gasCostChange'].error"
              color="primary"
              @change="onGasCostChange($event)"
            ></v-switch>
            <v-switch
              v-model="taxFreePeriod"
              class="settings-accounting__taxfree-period"
              :success-messages="settingsMessages['taxFreePeriod'].success"
              :error-messages="settingsMessages['taxFreePeriod'].error"
              label="Is there a tax free period?"
              color="primary"
              @change="onTaxFreeChange($event)"
            ></v-switch>
            <v-text-field
              v-model="taxFreeAfterPeriod"
              class="settings-accounting__taxfree-period-days"
              :success-messages="settingsMessages['taxFreePeriodAfter'].success"
              :error-messages="settingsMessages['taxFreePeriodAfter'].error"
              :disabled="!taxFreePeriod"
              :rules="taxFreeRules"
              label="Tax free after how many days"
              type="number"
              @change="onTaxFreePeriodChange($event)"
            >
            </v-text-field>
          </v-card-text>
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
                <asset-select
                  v-model="assetToIgnore"
                  label="Select asset to ignore"
                  :success-messages="settingsMessages['addIgnoreAsset'].success"
                  :error-messages="settingsMessages['addIgnoreAsset'].error"
                  hint="Click to see all assets and select one to ignore"
                  class="settings-accounting__asset-to-ignore"
                ></asset-select>
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
              <v-col cols="10" style="display: flex;">
                <asset-select
                  v-model="assetToRemove"
                  label="Select asset to remove from ignored assets"
                  value="test"
                  :items="ignoredAssets"
                  :success-messages="settingsMessages['remIgnoreAsset'].success"
                  :error-messages="settingsMessages['remIgnoreAsset'].error"
                  hint="Click to see all ignored assets and select one for removal"
                  class="settings-accounting__ignored-assets"
                ></asset-select>
                <div slot="append-outer">
                  <v-badge>
                    <template #badge>
                      <span class="settings-accounting__ignored-assets__badge">
                        {{ ignoredAssets.length }}
                      </span>
                    </template>
                  </v-badge>
                </div>
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
import { Component } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import { Message } from '@/store/store';

import { AccountingSettings } from '@/typing/types';
import Settings, { SettingsMessages } from '@/views/settings/Settings.vue';

const { mapState } = createNamespacedHelpers('session');

@Component({
  components: {
    MessageDialog,
    AssetSelect
  },
  computed: mapState(['accountingSettings'])
})
export default class Accounting extends Settings {
  accountingSettings!: AccountingSettings;

  crypto2CryptoTrades: boolean = false;
  gasCosts: boolean = false;
  taxFreeAfterPeriod: number | null = null;
  taxFreePeriod: boolean = false;

  ignoredAssets: string[] = [];
  assetToIgnore: string = '';
  assetToRemove: string = '';

  asset: string = '';

  settingsMessages: SettingsMessages = {
    crypto2crypto: { success: '', error: '' },
    gasCostChange: { success: '', error: '' },
    taxFreePeriod: { success: '', error: '' },
    taxFreePeriodAfter: { success: '', error: '' },
    addIgnoreAsset: { success: '', error: '' },
    remIgnoreAsset: { success: '', error: '' }
  };

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

  onTaxFreeChange(enabled: boolean) {
    let taxFreeAfterPeriod = this.taxFreeAfterPeriod;

    if (!enabled) {
      taxFreeAfterPeriod = null;
    } else {
      const period = this.accountingSettings.taxFreeAfterPeriod;
      if (period) {
        taxFreeAfterPeriod = period / 86400;
      } else {
        taxFreeAfterPeriod = 0;
      }
    }

    const { commit } = this.$store;
    if (taxFreeAfterPeriod !== null) {
      taxFreeAfterPeriod *= 86400;
    } else {
      taxFreeAfterPeriod = -1;
      this.taxFreeAfterPeriod = null;
    }
    this.$api
      .setSettings({ taxfree_after_period: taxFreeAfterPeriod! })
      .then(settings => {
        this.validateSettingChange(
          'taxFreePeriod',
          'success',
          `Tax free period ${enabled ? 'enabled' : 'disabled'}`
        );

        commit('session/accountingSettings', {
          ...this.accountingSettings,
          taxFreeAfterPeriod: settings.taxfree_after_period
        });
      })
      .catch((reason: Error) => {
        this.validateSettingChange(
          'taxFreePeriod',
          'error',
          `${reason.message}`
        );
        this.taxFreeAfterPeriod = null;
      });
  }

  onTaxFreePeriodChange(period: number) {
    if (period !== null) {
      period *= 86400;
    } else {
      period = -1;
    }

    const { commit } = this.$store;

    this.$api
      .setSettings({ taxfree_after_period: period })
      .then(settings => {
        this.validateSettingChange(
          'taxFreePeriodAfter',
          'success',
          `Tax free period set to ${this.taxFreeAfterPeriod} days`
        );

        commit('session/accountingSettings', {
          ...this.accountingSettings,
          taxFreeAfterPeriod: settings.taxfree_after_period
        });
      })
      .catch((reason: Error) => {
        this.validateSettingChange(
          'taxFreePeriodAfter',
          'error',
          `${reason.message}`
        );
        this.taxFreeAfterPeriod = null;
      });
  }

  onCrypto2CryptoChange(enabled: boolean) {
    const { commit } = this.$store;

    this.$api
      .setSettings({ include_crypto2crypto: enabled })
      .then(settings => {
        commit('session/accountingSettings', {
          ...this.accountingSettings,
          includeCrypto2Crypto: settings.include_crypto2crypto
        });
        this.validateSettingChange('crypto2crypto', 'success');
      })
      .catch(reason => {
        this.validateSettingChange(
          'crypto2crypto',
          'error',
          `Error setting crypto to crypto ${reason.message}`
        );
      });
  }

  onGasCostChange(enabled: boolean) {
    const { commit } = this.$store;

    this.$api
      .setSettings({ include_gas_costs: enabled })
      .then(settings => {
        commit('session/accountingSettings', {
          ...this.accountingSettings,
          includeGasCosts: settings.include_gas_costs
        });
        this.validateSettingChange('gasCostChange', 'success');
      })
      .catch(reason => {
        this.validateSettingChange(
          'gasCostChange',
          'error',
          `Error setting Ethereum gas costs: ${reason.message}`
        );
      });
  }

  addAsset() {
    this.$api
      .modifyAsset(true, this.assetToIgnore)
      .then(ignoredAssets => {
        this.ignoredAssets = ignoredAssets;
        this.validateSettingChange(
          'addIgnoreAsset',
          'success',
          `${this.assetToIgnore} added to ignored assets`
        );
        this.assetToIgnore = '';
      })
      .catch((reason: Error) => {
        this.validateSettingChange(
          'addIgnoreAsset',
          'error',
          `error adding ignored asset ${this.assetToIgnore} (${reason.message})`
        );
      });
  }

  removeAsset() {
    this.$api
      .modifyAsset(false, this.assetToRemove)
      .then(ignoredAssets => {
        this.ignoredAssets = ignoredAssets;
        this.validateSettingChange(
          'remIgnoreAsset',
          'success',
          `${this.assetToRemove} removed from ignored assets`
        );
        this.assetToRemove = '';
      })
      .catch((reason: Error) => {
        this.validateSettingChange(
          'remIgnoreAsset',
          'error',
          `error removing ignored asset ${this.assetToRemove} (${reason.message})`
        );
      });
  }
}
</script>

<style scoped></style>
