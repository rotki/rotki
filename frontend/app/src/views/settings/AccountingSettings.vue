<template>
  <div class="accounting-settings">
    <v-row no-gutters>
      <v-col>
        <card>
          <template #title>
            {{ $t('accounting_settings.title') }}
          </template>

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
            outlined
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
            :label="$t('accounting_settings.labels.calculate_past_cost_basis')"
            color="primary"
            @change="onCalculatePastCostBasisChange($event)"
          />
        </card>
      </v-col>
    </v-row>
    <v-row class="mt-8" no-gutters>
      <v-col>
        <card>
          <template #title>
            {{ $t('account_settings.asset_settings.title') }}
          </template>

          <v-row no-gutters>
            <v-col>
              <asset-select
                v-model="assetToIgnore"
                outlined
                :label="$t('account_settings.asset_settings.labels.ignore')"
                :success-messages="settingsMessages['addIgnoreAsset'].success"
                :error-messages="settingsMessages['addIgnoreAsset'].error"
                :hint="$t('account_settings.asset_settings.ignore_tags_hint')"
                class="accounting-settings__asset-to-ignore"
              />
            </v-col>
            <v-col cols="auto">
              <v-btn
                class="accounting-settings__buttons__add mt-3"
                text
                width="110px"
                color="primary"
                :disabled="assetToIgnore === ''"
                @click="addAsset()"
              >
                {{ $t('account_settings.asset_settings.actions.add') }}
              </v-btn>
            </v-col>
          </v-row>
          <v-row no-gutters>
            <v-col>
              <asset-select
                v-model="assetToRemove"
                outlined
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
            </v-col>
            <v-col cols="auto">
              <v-btn
                width="110px"
                class="accounting-settings__buttons__remove mt-3"
                text
                color="primary"
                :disabled="assetToRemove === ''"
                @click="removeAsset()"
              >
                {{ $t('account_settings.asset_settings.actions.remove') }}
              </v-btn>
            </v-col>
          </v-row>
          <v-row no-gutters>
            <v-col cols="auto">
              {{ $t('accounting_settings.ignored_assets') }}
            </v-col>
            <v-col>
              <v-badge class="pl-2">
                <template #badge>
                  <div class="accounting-settings__ignored-assets__badge">
                    {{ ignoredAssets.length }}
                  </div>
                </template>
              </v-badge>
            </v-col>
          </v-row>
        </card>
      </v-col>
    </v-row>
    <ledger-action-settings class="mt-18" />
    <v-row class="mt-8" no-gutters>
      <v-col>
        <card>
          <template #title>
            {{ $t('account_settings.csv_export_settings.title') }}
          </template>

          <v-switch
            v-model="exportCSVFormulas"
            class="csv_export_settings__exportCSVFormulas"
            :label="
              $t(
                'account_settings.csv_export_settings.labels.export_csv_formulas'
              )
            "
            color="primary"
            :success-messages="settingsMessages['exportCSVFormulas'].success"
            :error-messages="settingsMessages['exportCSVFormulas'].error"
            @change="onExportCSVFormulasChange($event)"
          />
          <v-switch
            v-model="haveCSVSummary"
            class="csv_export_settings__haveCSVSummary"
            :label="
              $t('account_settings.csv_export_settings.labels.have_csv_summary')
            "
            color="primary"
            :success-messages="settingsMessages['haveCSVSummary'].success"
            :error-messages="settingsMessages['haveCSVSummary'].error"
            @change="onHaveCSVSummaryChange($event)"
          />
        </card>
      </v-col>
    </v-row>
  </div>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { mapActions, mapState } from 'vuex';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import LedgerActionSettings from '@/components/settings/accounting/LedgerActionSettings.vue';
import { settingsMessages } from '@/components/settings/utils';
import AssetMixin from '@/mixins/asset-mixin';
import SettingsMixin from '@/mixins/settings-mixin';
import { ActionStatus } from '@/store/types';

const haveCSVSummary = 'haveCSVSummary';
const exportCSVFormulas = 'exportCSVFormulas';
const crypto2crypto = 'crypto2crypto';
const gasCostChange = 'gasCostChange';
const taxFreePeriod = 'taxFreePeriod';
const taxFreePeriodAfter = 'taxFreePeriodAfter';
const addIgnoreAsset = 'addIgnoreAsset';
const remIgnoreAsset = 'remIgnoreAsset';
const accountForAssetsMovements = 'accountForAssetsMovements';
const calculatePastCostBasis = 'calculatePastCostBasis';

const SETTINGS = [
  haveCSVSummary,
  exportCSVFormulas,
  crypto2crypto,
  gasCostChange,
  taxFreePeriod,
  taxFreePeriodAfter,
  addIgnoreAsset,
  remIgnoreAsset,
  accountForAssetsMovements,
  calculatePastCostBasis
] as const;

type SettingsEntries = typeof SETTINGS[number];

@Component({
  components: {
    LedgerActionSettings,
    AssetSelect
  },
  computed: {
    ...mapState('session', ['ignoredAssets'])
  },
  methods: {
    ...mapActions('session', ['ignoreAsset', 'unignoreAsset'])
  }
})
export default class Accounting extends Mixins<
  SettingsMixin<SettingsEntries> & AssetMixin
>(SettingsMixin, AssetMixin) {
  ignoredAssets!: string[];
  ignoreAsset!: (asset: string) => Promise<ActionStatus>;
  unignoreAsset!: (asset: string) => Promise<ActionStatus>;

  haveCSVSummary: boolean = false;
  exportCSVFormulas: boolean = false;
  crypto2CryptoTrades: boolean = false;
  gasCosts: boolean = false;
  taxFreeAfterPeriod: number | null = null;
  taxFreePeriod: boolean = false;
  accountForAssetsMovements: boolean = false;
  calculatePastCostBasis: boolean = false;

  assetToIgnore: string = '';
  assetToRemove: string = '';

  asset: string = '';

  taxFreeRules = [
    (v: string) => !!v || this.$tc('account_settings.validation.tax_free_days'),
    (v: string) =>
      (v && parseInt(v) > 0) ||
      this.$tc('account_settings.validation.tax_free_days_gt_zero')
  ];

  created() {
    this.settingsMessages = settingsMessages(SETTINGS);
  }

  mounted() {
    this.haveCSVSummary = this.accountingSettings.pnlCsvHaveSummary;
    this.exportCSVFormulas = this.accountingSettings.pnlCsvWithFormulas;
    this.crypto2CryptoTrades = this.accountingSettings.includeCrypto2crypto;
    this.gasCosts = this.accountingSettings.includeGasCosts;
    if (this.accountingSettings.taxfreeAfterPeriod) {
      this.taxFreePeriod = true;
      this.taxFreeAfterPeriod =
        this.accountingSettings.taxfreeAfterPeriod / 86400;
    } else {
      this.taxFreePeriod = false;
      this.taxFreeAfterPeriod = null;
    }
    this.accountForAssetsMovements =
      this.accountingSettings.accountForAssetsMovements;
    this.calculatePastCostBasis =
      this.accountingSettings.calculatePastCostBasis;
  }

  onTaxFreeChange(enabled: boolean) {
    let taxFreeAfterPeriod: number | null;

    if (!enabled) {
      taxFreeAfterPeriod = null;
    } else {
      const period = this.accountingSettings.taxfreeAfterPeriod;
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
      .setSettings({ taxfreeAfterPeriod: taxFreeAfterPeriod! })
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
          taxfreeAfterPeriod: settings.accounting.taxfreeAfterPeriod
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
      .setSettings({ taxfreeAfterPeriod: period })
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
          taxfreeAfterPeriod: settings.accounting.taxfreeAfterPeriod
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
      .setSettings({ includeCrypto2crypto: enabled })
      .then(settings => {
        commit('session/accountingSettings', {
          ...this.accountingSettings,
          includeCrypto2crypto: settings.accounting.includeCrypto2crypto
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
      .setSettings({ includeGasCosts: enabled })
      .then(settings => {
        commit('session/accountingSettings', {
          ...this.accountingSettings,
          includeGasCosts: settings.accounting.includeGasCosts
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
      .setSettings({ accountForAssetsMovements: enabled })
      .then(settings => {
        commit('session/accountingSettings', {
          ...this.accountingSettings,
          accountForAssetsMovements:
            settings.accounting.accountForAssetsMovements
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

  onHaveCSVSummaryChange(enabled: boolean) {
    const { commit } = this.$store;

    this.$api
      .setSettings({ pnlCsvHaveSummary: enabled })
      .then(settings => {
        commit('session/accountingSettings', {
          ...this.accountingSettings,
          pnlCsvHaveSummary: settings.accounting.pnlCsvHaveSummary
        });
        this.validateSettingChange('haveCSVSummary', 'success');
      })
      .catch(reason => {
        this.validateSettingChange(
          'haveCSVSummary',
          'error',
          this.$tc('account_settings.messages.have_csv_summary', 0, {
            message: reason.message
          })
        );
      });
  }

  onExportCSVFormulasChange(enabled: boolean) {
    const { commit } = this.$store;

    this.$api
      .setSettings({ pnlCsvWithFormulas: enabled })
      .then(settings => {
        commit('session/accountingSettings', {
          ...this.accountingSettings,
          pnlCsvWithFormulas: settings.accounting.pnlCsvWithFormulas
        });
        this.validateSettingChange('exportCSVFormulas', 'success');
      })
      .catch(reason => {
        this.validateSettingChange(
          'exportCSVFormulas',
          'error',
          this.$tc('account_settings.messages.export_csv_formulas', 0, {
            message: reason.message
          })
        );
      });
  }

  async onCalculatePastCostBasisChange(enabled: boolean) {
    const { success, message } = await this.settingsUpdate({
      calculatePastCostBasis: enabled
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
    const identifier = this.assetToIgnore;
    const { message, success } = await this.ignoreAsset(identifier);
    const asset = this.getSymbol(identifier);

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
    const identifier = this.assetToRemove;
    const { message, success } = await this.unignoreAsset(identifier);
    const asset = this.getSymbol(identifier);

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
