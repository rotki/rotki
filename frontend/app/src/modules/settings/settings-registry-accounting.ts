import { msg } from '@/message-key';
import { SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
import { accounting, type RegistryEntry } from '@/modules/settings/settings-channels';

/**
 * The `accounting` channel's registry slice: settings persisted on the backend `AccountingSettings`.
 * The accounting tab is flat (no category headers), so its two composite search rows carry a `tab`
 * search block on one representative key instead of a `category`.
 */
export const accountingRegistry = {
  calculatePastCostBasis: accounting('calculatePastCostBasis', { anchor: SettingsHighlightIds.ACCOUNTING_TRADE }),
  costBasisMethod: accounting('costBasisMethod', {
    anchor: SettingsHighlightIds.ACCOUNTING_TRADE,
    search: {
      keywords: [
        msg.$t('accounting_settings.trade.labels.include_crypto2crypto'),
        msg.$t('accounting_settings.trade.labels.include_gas_costs'),
        msg.$t('accounting_settings.trade.labels.tax_free'),
        msg.$t('accounting_settings.trade.labels.calculate_past_cost_basis'),
        msg.$t('accounting_settings.trade.labels.include_fees_in_cost_basis'),
        msg.$t('accounting_settings.trade.labels.cost_basis_method'),
        msg.$t('accounting_settings.trade.labels.eth_staking_taxable_after_withdrawal_enabled'),
      ],
      tab: '/settings/accounting/',
      titleKey: msg.$t('accounting_settings.trade.title'),
    },
  }),
  ethStakingTaxableAfterWithdrawalEnabled: accounting('ethStakingTaxableAfterWithdrawalEnabled', { anchor: SettingsHighlightIds.ACCOUNTING_TRADE }),
  includeCrypto2crypto: accounting('includeCrypto2crypto', { anchor: SettingsHighlightIds.ACCOUNTING_TRADE }),
  includeFeesInCostBasis: accounting('includeFeesInCostBasis', { anchor: SettingsHighlightIds.ACCOUNTING_TRADE }),
  includeGasCosts: accounting('includeGasCosts', { anchor: SettingsHighlightIds.ACCOUNTING_TRADE }),
  pnlCsvHaveSummary: accounting('pnlCsvHaveSummary', {
    anchor: SettingsHighlightIds.CSV_EXPORT,
    search: { tab: '/settings/accounting/', titleKey: msg.$t('account_settings.csv_export_settings.title') },
  }),
  pnlCsvWithFormulas: accounting('pnlCsvWithFormulas', { anchor: SettingsHighlightIds.CSV_EXPORT }),
  taxfreeAfterPeriod: accounting('taxfreeAfterPeriod', { anchor: SettingsHighlightIds.ACCOUNTING_TRADE }),
  useAssetCollectionsInCostBasis: accounting('useAssetCollectionsInCostBasis', { anchor: SettingsHighlightIds.ACCOUNTING_TRADE }),
} satisfies Record<string, RegistryEntry>;
