<template>
  <v-container class="accounting-settings">
    <v-row no-gutters>
      <v-col>
        <v-card>
          <v-card-title>{{ $t('accounting_settings.title') }}</v-card-title>
          <v-card-text>
            <v-switch
              v-model="crypto2CryptoTrades"
              class="accounting-settings__crypto2crypto"
              :label="$t('accounting_settings.labels.crypto_to_crypto')"
              color="primary"
              :success-messages="settingsMessages['crypto2crypto'].success"
              :error-messages="settingsMessages['crypto2crypto'].error"
              @change="onCrypto2CryptoChange($event)"
            />
            <v-switch
              v-model="gasCosts"
              class="accounting-settings__include-gas-costs"
              :label="$t('accounting_settings.labels.gas_costs')"
              :success-messages="settingsMessages['gasCostChange'].success"
              :error-messages="settingsMessages['gasCostChange'].error"
              color="primary"
              @change="onGasCostChange($event)"
            />
            <v-switch
              v-model="taxFreePeriod"
              class="accounting-settings__taxfree-period"
              :success-messages="settingsMessages['taxFreePeriod'].success"
              :error-messages="settingsMessages['taxFreePeriod'].error"
              :label="$t('accounting_settings.labels.tax_free')"
              color="primary"
              @change="onTaxFreeChange($event)"
            />
            <v-text-field
              v-model="taxFreeAfterPeriod"
              class="accounting-settings__taxfree-period-days"
              :success-messages="settingsMessages['taxFreePeriodAfter'].success"
              :error-messages="settingsMessages['taxFreePeriodAfter'].error"
              :disabled="!taxFreePeriod"
              :rules="taxFreeRules"
              :label="$t('accounting_settings.labels.tax_free_period')"
              type="number"
              @change="onTaxFreePeriodChange($event)"
            />
            <v-switch
              v-model="accountForAssetsMovements"
              class="accounting-settings__account-for-assets-movements"
              :success-messages="
                settingsMessages['accountForAssetsMovements'].success
              "
              :error-messages="
                settingsMessages['accountForAssetsMovements'].error
              "
              :label="
                $t('accounting_settings.labels.account_for_assets_movements')
              "
              color="primary"
              @change="onAccountForAssetsMovements($event)"
            />
            <v-switch
              v-model="calculatePastCostBasis"
              class="accounting-settings__past-cost-basis"
              :success-messages="
                settingsMessages['calculatePastCostBasis'].success
              "
              :error-messages="settingsMessages['calculatePastCostBasis'].error"
              :label="
                $t('accounting_settings.labels.calculate_past_cost_basis')
              "
              color="primary"
              @change="onCalculatePastCostBasisChange($event)"
            />
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    <v-row class="mt-4">
      <v-col>
        <v-card>
          <v-card-title>
            {{ $t('account_settings.asset_settings.title') }}
          </v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="10">
                <asset-select
                  v-model="assetToIgnore"
                  :label="$t('account_settings.asset_settings.labels.ignore')"
                  :success-messages="settingsMessages['addIgnoreAsset'].success"
                  :error-messages="settingsMessages['addIgnoreAsset'].error"
                  :hint="$t('account_settings.asset_settings.ignore_tags_hint')"
                  class="accounting-settings__asset-to-ignore"
                />
              </v-col>
              <v-col cols="2">
                <v-btn
                  class="accounting-settings__buttons__add"
                  text
                  color="primary"
                  :disabled="assetToIgnore === ''"
                  @click="addAsset()"
                >
                  {{ $t('account_settings.asset_settings.actions.add') }}
                </v-btn>
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="10" class="d-flex">
                <asset-select
                  v-model="assetToRemove"
                  :label="$t('account_settings.asset_settings.labels.unignore')"
                  value="test"
                  :items="ignoredAssets"
                  :success-messages="settingsMessages['remIgnoreAsset'].success"
                  :error-messages="settingsMessages['remIgnoreAsset'].error"
                  :hint="
                    $t('account_settings.asset_settings.labels.unignore_hint')
                  "
                  class="accounting-settings__ignored-assets"
                />
                <div slot="append-outer">
                  <v-badge>
                    <template #badge>
                      <span class="accounting-settings__ignored-assets__badge">
                        {{ ignoredAssets.length }}
                      </span>
                    </template>
                  </v-badge>
                </div>
              </v-col>
              <v-col cols="2">
                <v-btn
                  class="accounting-settings__buttons__remove"
                  text
                  color="primary"
                  :disabled="assetToRemove === ''"
                  @click="removeAsset()"
                >
                  {{ $t('account_settings.asset_settings.actions.remove') }}
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
import { mapActions, mapState } from 'vuex';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import { ActionStatus } from '@/store/types';
import { AccountingSettings, SettingsUpdate } from '@/typing/types';
import Settings, { SettingsMessages } from '@/views/settings/Settings.vue';

@Component({
  components: {
    AssetSelect
  },
  computed: {
    ...mapState('session', ['accountingSettings', 'ignoredAssets'])
  },
  methods: {
    ...mapActions('session', ['ignoreAsset', 'unignoreAsset', 'settingsUpdate'])
  }
})
export default class Accounting extends Settings {
  accountingSettings!: AccountingSettings;
  ignoredAssets!: string[];
  ignoreAsset!: (asset: string) => Promise<ActionStatus>;
  unignoreAsset!: (asset: string) => Promise<ActionStatus>;
  settingsUpdate!: (update: SettingsUpdate) => Promise<ActionStatus>;

  crypto2CryptoTrades: boolean = false;
  gasCosts: boolean = false;
  taxFreeAfterPeriod: number | null = null;
  taxFreePeriod: boolean = false;
  accountForAssetsMovements: boolean = false;
  calculatePastCostBasis: boolean = false;

  assetToIgnore: string = '';
  assetToRemove: string = '';

  asset: string = '';

  settingsMessages: SettingsMessages = {
    crypto2crypto: { success: '', error: '' },
    gasCostChange: { success: '', error: '' },
    taxFreePeriod: { success: '', error: '' },
    taxFreePeriodAfter: { success: '', error: '' },
    addIgnoreAsset: { success: '', error: '' },
    remIgnoreAsset: { success: '', error: '' },
    accountForAssetsMovements: { success: '', error: '' },
    calculatePastCostBasis: { success: '', error: '' }
  };

  taxFreeRules = [
    (v: string) => !!v || this.$tc('account_settings.validation.tax_free_days'),
    (v: string) =>
      (v && parseInt(v) > 0) ||
      this.$tc('account_settings.validation.tax_free_days_gt_zero')
  ];

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
    this.accountForAssetsMovements = this.accountingSettings.accountForAssetsMovements;
    this.calculatePastCostBasis = this.accountingSettings.calculatePastCostBasis;
  }

  onTaxFreeChange(enabled: boolean) {
    let taxFreeAfterPeriod: number | null;

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
          this.$tc('account_settings.messages.tax_free', 0, {
            enabled: enabled ? 'enabled' : 'disabled'
          })
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
          this.$tc('account_settings.messages.tax_free_period', 0, {
            period: this.taxFreeAfterPeriod
          })
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
          this.$tc('account_settings.messages.crypto_to_crypto', 0, {
            message: reason.message
          })
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
          this.$tc('account_settings.messages.gas_costs', 0, {
            message: reason.message
          })
        );
      });
  }

  onAccountForAssetsMovements(enabled: boolean) {
    const { commit } = this.$store;

    this.$api
      .setSettings({ account_for_assets_movements: enabled })
      .then(settings => {
        commit('session/accountingSettings', {
          ...this.accountingSettings,
          accountForAssetsMovements: settings.account_for_assets_movements
        });
        this.validateSettingChange('accountForAssetsMovements', 'success');
      })
      .catch(reason => {
        this.validateSettingChange(
          'accountForAssetsMovements',
          'error',
          this.$tc(
            'account_settings.messages.account_for_assets_movements',
            0,
            {
              message: reason.message
            }
          )
        );
      });
  }

  async onCalculatePastCostBasisChange(enabled: boolean) {
    const { success, message } = await this.settingsUpdate({
      calculate_past_cost_basis: enabled
    });
    this.validateSettingChange(
      'calculatePastCostBasis',
      success ? 'success' : 'error',
      success
        ? enabled
          ? this.$t('account_settings.messages.cost_basics.enabled').toString()
          : this.$t('account_settings.messages.cost_basics.disabled').toString()
        : this.$t('account_settings.messages.cost_basics.error', {
            message
          }).toString()
    );
  }

  async addAsset() {
    const asset = this.assetToIgnore;
    const { message, success } = await this.ignoreAsset(asset);

    const validationMessage = success
      ? this.$tc('account_settings.messages.ignored_success', 0, { asset })
      : this.$tc('account_settings.messages.ignored_failure', 0, {
          asset,
          message
        });
    this.validateSettingChange(
      'addIgnoreAsset',
      success ? 'success' : 'error',
      validationMessage
    );

    if (success) {
      this.assetToIgnore = '';
    }
  }

  async removeAsset() {
    const asset = this.assetToRemove;
    const { message, success } = await this.unignoreAsset(asset);

    const validationMessage = success
      ? this.$tc('account_settings.messages.unignored_success', 0, { asset })
      : this.$tc('account_settings.messages.unignored_failure', 0, {
          asset,
          message
        });

    this.validateSettingChange(
      'remIgnoreAsset',
      success ? 'success' : 'error',
      validationMessage
    );

    if (success) {
      this.assetToRemove = '';
    }
  }
}
</script>
