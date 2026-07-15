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
  /**
   * When set, the category's member rows omit the category title from their breadcrumb (tab > row
   * instead of tab > category > row). The header row still shows. Matches a flat settings page whose
   * settings are not visually nested under a category heading (the interface tab).
   */
  readonly flat?: boolean;
}

/**
 * Category header rows for registry-derived search. Each entry contributes its header row; its per-setting
 * member rows come from the registry `search` blocks and its non-registry rows from `settingsActions`.
 */
export const SEARCH_CATEGORIES: readonly SearchCategory[] = [
  // account
  {
    id: SettingsCategoryIds.SECURITY,
    keywords: [msg.$t('settings.security_settings.subtitle')],
    tab: '/settings/account/',
    titleKey: msg.$t('settings.security_settings.title'),
  },
  // general
  {
    id: SettingsCategoryIds.GENERAL,
    keywords: [msg.$t('general_settings.subtitle')],
    tab: '/settings/general/',
    titleKey: msg.$t('general_settings.title'),
  },
  {
    id: SettingsCategoryIds.AMOUNT,
    keywords: [msg.$t('general_settings.amount.subtitle')],
    tab: '/settings/general/',
    titleKey: msg.$t('general_settings.amount.title'),
  },
  {
    id: SettingsCategoryIds.NFT,
    tab: '/settings/general/',
    titleKey: msg.$t('general_settings.nft_setting.title'),
  },
  {
    id: SettingsCategoryIds.HISTORY_EVENT,
    keywords: [msg.$t('general_settings.history_event.subtitle')],
    tab: '/settings/general/',
    titleKey: msg.$t('general_settings.history_event.title'),
  },
  {
    id: SettingsCategoryIds.EXTERNAL_SERVICE,
    keywords: [msg.$t('general_settings.external_service_setting.subtitle')],
    tab: '/settings/general/',
    titleKey: msg.$t('general_settings.external_service_setting.title'),
  },
  {
    id: SettingsCategoryIds.BACKEND,
    keywords: [msg.$t('backend_settings.subtitle')],
    tab: '/settings/general/',
    titleKey: msg.$t('backend_settings.title'),
  },
  // database
  {
    id: SettingsCategoryIds.DATABASE_INFO,
    keywords: [msg.$t('database_settings.database_info.subtitle')],
    tab: '/settings/database/',
    titleKey: msg.$t('database_settings.database_info.title'),
  },
  {
    id: SettingsCategoryIds.USER_BACKUPS,
    keywords: [msg.$t('database_settings.user_backups.subtitle')],
    tab: '/settings/database/',
    titleKey: msg.$t('database_settings.user_backups.title'),
  },
  {
    id: SettingsCategoryIds.MANAGE_DATA,
    keywords: [msg.$t('database_settings.manage_data.subtitle')],
    tab: '/settings/database/',
    titleKey: msg.$t('database_settings.manage_data.title'),
  },
  {
    id: SettingsCategoryIds.IMPORT_EXPORT,
    keywords: [msg.$t('database_settings.import_export.subtitle')],
    tab: '/settings/database/',
    titleKey: msg.$t('database_settings.import_export.title'),
  },
  {
    id: SettingsCategoryIds.ASSET_DATABASE,
    keywords: [msg.$t('database_settings.asset_database.subtitle')],
    tab: '/settings/database/',
    titleKey: msg.$t('database_settings.asset_database.title'),
  },
  // evm
  {
    id: SettingsCategoryIds.CHAINS,
    tab: '/settings/evm/',
    titleKey: msg.$t('evm_settings.general.title'),
  },
  {
    id: SettingsCategoryIds.INDEXER,
    keywords: [msg.$t('evm_settings.indexer.subtitle')],
    tab: '/settings/evm/',
    titleKey: msg.$t('evm_settings.indexer.title'),
  },
  // oracle
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
  // interface - a flat page: its top-level settings sit directly under the tab (no category segment),
  // while the graph and newly-detected-tokens panels nest their settings under a header as usual.
  {
    flat: true,
    id: SettingsCategoryIds.INTERFACE_ONLY,
    tab: '/settings/interface/',
    titleKey: msg.$t('frontend_settings.title'),
  },
  {
    id: SettingsCategoryIds.GRAPH,
    keywords: [msg.$t('frontend_settings.subtitle.graph_settings_hint')],
    tab: '/settings/interface/',
    titleKey: msg.$t('frontend_settings.subtitle.graph_settings'),
  },
  {
    id: SettingsCategoryIds.ALIAS,
    tab: '/settings/interface/',
    titleKey: msg.$t('frontend_settings.subtitle.alias_names'),
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
