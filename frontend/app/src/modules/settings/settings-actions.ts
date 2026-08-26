import type { SettingKey } from '@/modules/settings/use-setting';
import type { RouteName } from '@/types/router';
import { type MessageKey, msg } from '@/message-key';
import { type SettingsCategoryId, SettingsCategoryIds, type SettingsHighlightId, SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
import { getRegistryEntry } from '@/modules/settings/settings-registry';

/**
 * A settings-search row that is not backed by a registry value: an action target (purge, change
 * password), an info display (db versions, latest/historic prices) or a categoryless section (accounting
 * rules, rpc nodes, modules). Keyed like the registry so a template single-sources its scroll-target id
 * through `anchorId(key)` and the search deriver reads it the same way it reads registry `search` blocks.
 * A `category` row nests under that category's header, giving a tab/category/row breadcrumb, while a
 * `tab` row sits directly on its tab. Pure info rows omit `anchor`, having no scroll target.
 */
export interface ActionEntry {
  readonly anchor?: SettingsHighlightId;
  readonly category?: SettingsCategoryId;
  readonly group?: MessageKey;
  readonly keywords?: readonly MessageKey[];
  readonly tab?: RouteName;
  readonly titleKey: MessageKey;
}

/**
 * The non-registry settings-search rows, the counterpart to the settings registry. Every anchored entry
 * owns exactly one `SettingsHighlightId` that no registry setting owns (enforced by the search spec's
 * ownership invariant), so adding or renaming an action is a one-line change here.
 */
export const settingsActions = {
  accountingRule: {
    anchor: SettingsHighlightIds.ACCOUNTING_RULE,
    keywords: [msg.$t('accounting_settings.rule.subtitle')],
    tab: '/settings/accounting/',
    titleKey: msg.$t('accounting_settings.rule.title'),
  },
  assetUpdate: {
    anchor: SettingsHighlightIds.ASSET_UPDATE,
    category: SettingsCategoryIds.ASSET_DATABASE,
    keywords: [msg.$t('asset_update.manual.subtitle')],
    titleKey: msg.$t('asset_update.manual.title'),
  },
  changePassword: {
    anchor: SettingsHighlightIds.CHANGE_PASSWORD,
    category: SettingsCategoryIds.SECURITY,
    keywords: [msg.$t('change_password.subtitle')],
    titleKey: msg.$t('change_password.title'),
  },
  globalDbInfo: {
    anchor: SettingsHighlightIds.GLOBALDB_INFO,
    category: SettingsCategoryIds.DATABASE_INFO,
    titleKey: msg.$t('database_settings.database_info.labels.globaldb'),
  },
  historicPrices: {
    category: SettingsCategoryIds.PRICE_ORACLE,
    titleKey: msg.$t('price_oracle_settings.historic_prices'),
  },
  historyQueryIndicator: {
    category: SettingsCategoryIds.INTERFACE_ONLY,
    titleKey: msg.$t('frontend_settings.history_query_indicator.title'),
  },
  latestPrices: {
    category: SettingsCategoryIds.PRICE_ORACLE,
    titleKey: msg.$t('price_oracle_settings.latest_prices'),
  },
  logLevel: {
    anchor: SettingsHighlightIds.LOG_LEVEL,
    category: SettingsCategoryIds.BACKEND,
    keywords: [msg.$t('backend_settings.settings.log_level.hint')],
    titleKey: msg.$t('backend_settings.settings.log_level.label'),
  },
  mcpServer: {
    anchor: SettingsHighlightIds.MCP_SERVER,
    keywords: [msg.$t('backend_settings.settings.mcp_server.hint')],
    tab: '/settings/mcp/',
    titleKey: msg.$t('backend_settings.settings.mcp_server.label'),
  },
  modules: {
    anchor: SettingsHighlightIds.MODULES,
    keywords: [msg.$t('module_settings.subtitle')],
    tab: '/settings/modules/',
    titleKey: msg.$t('module_settings.title'),
  },
  purgeData: {
    anchor: SettingsHighlightIds.PURGE_DATA,
    category: SettingsCategoryIds.MANAGE_DATA,
    keywords: [msg.$t('data_management.purge_data.subtitle')],
    titleKey: msg.$t('data_management.purge_data.title'),
  },
  purgeImagesCache: {
    anchor: SettingsHighlightIds.PURGE_IMAGES_CACHE,
    category: SettingsCategoryIds.MANAGE_DATA,
    keywords: [msg.$t('data_management.purge_images_cache.subtitle')],
    titleKey: msg.$t('data_management.purge_images_cache.title'),
  },
  refreshCache: {
    anchor: SettingsHighlightIds.REFRESH_CACHE,
    category: SettingsCategoryIds.MANAGE_DATA,
    keywords: [msg.$t('data_management.refresh_cache.subtitle')],
    titleKey: msg.$t('data_management.refresh_cache.title'),
  },
  resetDismissalStatus: {
    anchor: SettingsHighlightIds.RESET_DISMISSAL_STATUS,
    category: SettingsCategoryIds.INTERFACE_ONLY,
    group: msg.$t('frontend_settings.history_query_indicator.title'),
    keywords: [msg.$t('frontend_settings.history_query_indicator.reset_dismissal_status.subtitle')],
    titleKey: msg.$t('frontend_settings.history_query_indicator.reset_dismissal_status.title'),
  },
  restoreAssetsDb: {
    anchor: SettingsHighlightIds.RESTORE_ASSETS_DB,
    category: SettingsCategoryIds.ASSET_DATABASE,
    keywords: [msg.$t('asset_update.restore.subtitle')],
    titleKey: msg.$t('asset_update.restore.title'),
  },
  rpcNodes: {
    anchor: SettingsHighlightIds.RPC_NODES,
    keywords: [msg.$t('general_settings.rpc_node_setting.subtitle')],
    tab: '/settings/rpc/',
    titleKey: msg.$t('general_settings.rpc_node_setting.title'),
  },
  skippedEvents: {
    anchor: SettingsHighlightIds.SKIPPED_EVENTS,
    category: SettingsCategoryIds.HISTORY_EVENT,
    keywords: [msg.$t('general_settings.history_event.skipped_events.subtitle')],
    titleKey: msg.$t('general_settings.history_event.skipped_events.title'),
  },
  userDbInfo: {
    anchor: SettingsHighlightIds.USERDB_INFO,
    category: SettingsCategoryIds.DATABASE_INFO,
    titleKey: msg.$t('database_settings.database_info.labels.userdb'),
  },
} satisfies Record<string, ActionEntry>;

export type ActionKey = keyof typeof settingsActions;

/**
 * Actions keyed for lookup. A `Map` built from `Object.entries` types its values as `ActionEntry`
 * without an assertion, mirroring the settings registry's `registryByKey`.
 */
const actionsByKey: ReadonlyMap<string, ActionEntry> = new Map(Object.entries(settingsActions));

/** Resolves an action entry by key (mirrors `getRegistryEntry`; a valid `ActionKey` always resolves). */
export function getActionEntry(key: ActionKey): ActionEntry | undefined {
  return actionsByKey.get(key);
}

/** All action entries as typed `[key, entry]` pairs (a bare `Object.entries` widens the value to a union). */
export function actionEntries(): ReadonlyArray<readonly [string, ActionEntry]> {
  return [...actionsByKey];
}

/**
 * The scroll-target DOM id for a settings search anchor, resolved from whichever registry owns the key:
 * an action target from `settingsActions`, otherwise a setting from the settings registry. This is the
 * single id resolver shared by `SettingsItem` and the bare section anchors, so no template restates a
 * `SettingsHighlightIds` value.
 */
export function anchorId(key: SettingKey | ActionKey): string | undefined {
  return actionsByKey.get(key)?.anchor ?? getRegistryEntry(key)?.anchor;
}

/**
 * Reverse index: the action keys that own a given anchor. Composite anchors never appear here (they are
 * registry-owned); a keyless action target resolves to its one key. Used by the search spec to assert
 * every highlight id is owned by exactly one of the two registries.
 */
export function actionKeysForAnchor(anchor: SettingsHighlightId): string[] {
  return actionEntries()
    .filter(([, entry]) => entry.anchor === anchor)
    .map(([key]) => key);
}
