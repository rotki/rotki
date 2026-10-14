import { msg } from '@/message-key';
import { SettingsCategoryIds, SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
import { accounting, type RegistryEntry } from '@/modules/settings/settings-channels';

/**
 * The `accounting` channel's registry slice: settings persisted on the backend `AccountingSettings`.
 * Each setting is a row of its own under the cost basis, taxes or CSV export section, titled by its
 * short name and found by its longer switch label too.
 */
export const accountingRegistry = {
  calculatePastCostBasis: accounting('calculatePastCostBasis', {
    anchor: SettingsHighlightIds.PAST_COST_BASIS,
    search: {
      category: SettingsCategoryIds.COST_BASIS,
      keywords: [msg.$t('accounting_settings.trade.labels.calculate_past_cost_basis')],
      titleKey: msg.$t('accounting_settings.trade.titles.calculate_past_cost_basis'),
    },
  }),
  costBasisMethod: accounting('costBasisMethod', {
    anchor: SettingsHighlightIds.COST_BASIS_METHOD,
    search: {
      category: SettingsCategoryIds.COST_BASIS,
      titleKey: msg.$t('accounting_settings.trade.titles.cost_basis_method'),
    },
  }),
  ethStakingTaxableAfterWithdrawalEnabled: accounting('ethStakingTaxableAfterWithdrawalEnabled', {
    anchor: SettingsHighlightIds.ETH_STAKING_TAXABLE,
    search: {
      category: SettingsCategoryIds.TAXES,
      keywords: [msg.$t('accounting_settings.trade.labels.eth_staking_taxable_after_withdrawal_enabled')],
      titleKey: msg.$t('accounting_settings.trade.titles.eth_staking_taxable_after_withdrawal_enabled'),
    },
  }),
  includeCrypto2crypto: accounting('includeCrypto2crypto', {
    anchor: SettingsHighlightIds.CRYPTO_TO_CRYPTO,
    search: {
      category: SettingsCategoryIds.TAXES,
      keywords: [msg.$t('accounting_settings.trade.labels.include_crypto2crypto')],
      titleKey: msg.$t('accounting_settings.trade.titles.include_crypto2crypto'),
    },
  }),
  includeFeesInCostBasis: accounting('includeFeesInCostBasis', {
    anchor: SettingsHighlightIds.COST_BASIS_FEES,
    search: {
      category: SettingsCategoryIds.COST_BASIS,
      keywords: [msg.$t('accounting_settings.trade.labels.include_fees_in_cost_basis')],
      titleKey: msg.$t('accounting_settings.trade.titles.include_fees_in_cost_basis'),
    },
  }),
  includeGasCosts: accounting('includeGasCosts', {
    anchor: SettingsHighlightIds.GAS_COSTS,
    search: {
      category: SettingsCategoryIds.TAXES,
      keywords: [msg.$t('accounting_settings.trade.labels.include_gas_costs')],
      titleKey: msg.$t('accounting_settings.trade.titles.include_gas_costs'),
    },
  }),
  pnlCsvHaveSummary: accounting('pnlCsvHaveSummary', {
    anchor: SettingsHighlightIds.PNL_CSV_SUMMARY,
    search: {
      category: SettingsCategoryIds.PNL_CSV,
      keywords: [msg.$t('account_settings.csv_export_settings.labels.have_csv_summary')],
      titleKey: msg.$t('account_settings.csv_export_settings.titles.have_csv_summary'),
    },
  }),
  pnlCsvWithFormulas: accounting('pnlCsvWithFormulas', {
    anchor: SettingsHighlightIds.PNL_CSV_FORMULAS,
    search: {
      category: SettingsCategoryIds.PNL_CSV,
      keywords: [msg.$t('account_settings.csv_export_settings.labels.export_csv_formulas')],
      titleKey: msg.$t('account_settings.csv_export_settings.titles.export_csv_formulas'),
    },
  }),
  taxfreeAfterPeriod: accounting('taxfreeAfterPeriod', {
    anchor: SettingsHighlightIds.TAX_FREE_PERIOD,
    search: {
      category: SettingsCategoryIds.TAXES,
      keywords: [msg.$t('accounting_settings.trade.labels.tax_free')],
      titleKey: msg.$t('accounting_settings.trade.titles.tax_free'),
    },
  }),
  useAssetCollectionsInCostBasis: accounting('useAssetCollectionsInCostBasis', {
    anchor: SettingsHighlightIds.ASSET_COLLECTIONS,
    search: {
      category: SettingsCategoryIds.COST_BASIS,
      keywords: [msg.$t('accounting_settings.trade.labels.use_asset_collections_in_cost_basis')],
      titleKey: msg.$t('accounting_settings.trade.titles.use_asset_collections_in_cost_basis'),
    },
  }),
} satisfies Record<string, RegistryEntry>;
