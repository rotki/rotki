import type { RouteName } from '@/types/router';
import { type MessageKey, msg } from '@/message-key';
import { type SettingsCategoryId, SettingsCategoryIds } from '@/modules/settings/setting-highlight-ids';

/**
 * A settings category that sources its per-setting rows from the registry. It declares the owning tab
 * and header title - the one structural fact not carried on an individual setting. The tab's
 * route/label/icon still come from the page `nav` meta via `tabInfo`, so nothing about the tab is
 * restated. A category with no registry settings (backups, import/export, alias, theme) still lists
 * here to contribute its header row.
 */
export interface SearchCategory {
  readonly id: SettingsCategoryId;
  readonly tab: RouteName;
  readonly titleKey: MessageKey;
  readonly keywords?: readonly MessageKey[];
}

/**
 * Category header rows for registry-derived search. Each entry contributes its header row; its per-setting
 * member rows come from the registry `search` blocks and its non-registry rows from `settingsActions`.
 */
export const SEARCH_CATEGORIES: readonly SearchCategory[] = [
  // account
  {
    id: SettingsCategoryIds.SECURITY,
    tab: '/settings/account/',
    titleKey: msg.$t('settings.security_settings.title'),
  },
  {
    id: SettingsCategoryIds.GENERAL,
    keywords: [msg.$t('backend_settings.title')],
    tab: '/settings/general/',
    titleKey: msg.$t('general_settings.application.title'),
  },
  {
    id: SettingsCategoryIds.TOKENS_BALANCES,
    tab: '/settings/general/',
    titleKey: msg.$t('general_settings.tokens_balances.title'),
  },
  {
    id: SettingsCategoryIds.AMOUNT,
    tab: '/settings/general/',
    titleKey: msg.$t('general_settings.formats.title'),
  },
  {
    id: SettingsCategoryIds.NFT,
    tab: '/settings/general/',
    titleKey: msg.$t('general_settings.nft_setting.title'),
  },
  {
    id: SettingsCategoryIds.HISTORY_EVENT,
    tab: '/settings/general/',
    titleKey: msg.$t('general_settings.history_event.title'),
  },
  {
    id: SettingsCategoryIds.EXTERNAL_SERVICE,
    tab: '/settings/general/',
    titleKey: msg.$t('general_settings.external_service_setting.title'),
  },
  {
    id: SettingsCategoryIds.DATABASE_INFO,
    tab: '/settings/database/',
    titleKey: msg.$t('database_settings.database_info.title'),
  },
  {
    id: SettingsCategoryIds.USER_BACKUPS,
    tab: '/settings/database/',
    titleKey: msg.$t('database_settings.user_backups.title'),
  },
  {
    id: SettingsCategoryIds.ASSET_DATABASE,
    keywords: [msg.$t('manage_user_assets.export.title'), msg.$t('common.actions.import')],
    tab: '/settings/database/',
    titleKey: msg.$t('database_settings.asset_database.title'),
  },
  {
    id: SettingsCategoryIds.MANAGE_DATA,
    tab: '/settings/database/',
    titleKey: msg.$t('database_settings.manage_data.title'),
  },
  // accounting
  {
    id: SettingsCategoryIds.COST_BASIS,
    tab: '/settings/accounting/',
    titleKey: msg.$t('accounting_settings.cost_basis.title'),
  },
  {
    id: SettingsCategoryIds.TAXES,
    tab: '/settings/accounting/',
    titleKey: msg.$t('accounting_settings.taxes.title'),
  },
  {
    id: SettingsCategoryIds.PNL_CSV,
    tab: '/settings/accounting/',
    titleKey: msg.$t('account_settings.csv_export_settings.title'),
  },
  // chains
  {
    id: SettingsCategoryIds.CHAIN_QUERIES,
    tab: '/settings/chains/',
    titleKey: msg.$t('chain_settings.chain_queries.title'),
  },
  {
    id: SettingsCategoryIds.INDEXER,
    tab: '/settings/chains/',
    titleKey: msg.$t('evm_settings.indexer.title'),
  },
  {
    id: SettingsCategoryIds.PRICE_ORACLE,
    keywords: [msg.$t('price_oracle_settings.subtitle')],
    tab: '/settings/oracle/',
    titleKey: msg.$t('price_oracle_settings.title'),
  },
  {
    id: SettingsCategoryIds.PENALTY,
    keywords: [msg.$t('oracle_cache_management.penalty.subtitle')],
    tab: '/settings/oracle/',
    titleKey: msg.$t('oracle_cache_management.penalty.title'),
  },
  {
    id: SettingsCategoryIds.INTERFACE_ONLY,
    tab: '/settings/interface/',
    titleKey: msg.$t('frontend_settings.sections.display'),
  },
  {
    id: SettingsCategoryIds.PRIVACY,
    tab: '/settings/interface/',
    titleKey: msg.$t('frontend_settings.sections.privacy'),
  },
  {
    id: SettingsCategoryIds.REFRESH,
    tab: '/settings/interface/',
    titleKey: msg.$t('frontend_settings.sections.refresh'),
  },
  {
    id: SettingsCategoryIds.GRAPH,
    tab: '/settings/interface/',
    titleKey: msg.$t('frontend_settings.sections.graphs'),
  },
  {
    id: SettingsCategoryIds.ALIAS,
    tab: '/settings/interface/',
    titleKey: msg.$t('frontend_settings.sections.addresses'),
  },
  {
    id: SettingsCategoryIds.NEWLY_DETECTED_TOKENS,
    keywords: [msg.$t('frontend_settings.newly_detected_tokens.subtitle')],
    tab: '/settings/interface/',
    titleKey: msg.$t('frontend_settings.newly_detected_tokens.title'),
  },
  {
    id: SettingsCategoryIds.THEME,
    keywords: [msg.$t('premium_components.theme_manager.text_hint')],
    tab: '/settings/interface/',
    titleKey: msg.$t('premium_components.theme_manager.text'),
  },
];
