import type { RuiIcons } from '@rotki/ui-library';
import type { Ref } from 'vue';
import type { RouteLocationRaw } from 'vue-router';
import { getTextToken } from '@rotki/common';
import { type SettingsCategoryId, SettingsCategoryIds, type SettingsHighlightId, SettingsHighlightIds, type SettingsSearchEntry } from '@/modules/settings/setting-highlight-ids';
import { useAppRoutes } from '@/router/routes';

interface TabInfo {
  icon: RuiIcons;
  text: string;
  route: RouteLocationRaw;
}

interface EntryDef {
  texts: string[];
  highlightId?: SettingsHighlightId;
  keywords?: string[];
}

interface CategoryDef {
  categoryId?: SettingsCategoryId;
  children: EntryDef[];
}

interface TabGroup {
  tab: TabInfo;
  categories: CategoryDef[];
}

type T = ReturnType<typeof useI18n>['t'];

interface UseSettingsSearchReturn {
  entries: Readonly<Ref<SettingsSearchEntry[]>>;
  filterEntries: (entries: SettingsSearchEntry[], keyword: string) => SettingsSearchEntry[];
}

interface SettingsRoutes {
  SETTINGS_ACCOUNT: TabInfo;
  SETTINGS_GENERAL: TabInfo;
  SETTINGS_DATABASE: TabInfo;
  SETTINGS_ACCOUNTING: TabInfo;
  SETTINGS_EVM: TabInfo;
  SETTINGS_ORACLE: TabInfo;
  SETTINGS_RPC: TabInfo;
  SETTINGS_MODULES: TabInfo;
  SETTINGS_INTERFACE: TabInfo;
}

function getAccountTab(routes: SettingsRoutes, t: T): TabGroup {
  return { tab: routes.SETTINGS_ACCOUNT, categories: [
    { categoryId: SettingsCategoryIds.SECURITY, children: [
      { texts: [t('settings.security_settings.title')], keywords: [t('settings.security_settings.subtitle')] },
      { texts: [t('settings.security_settings.title'), t('change_password.title')], keywords: [t('change_password.subtitle')], highlightId: SettingsHighlightIds.CHANGE_PASSWORD },
      { texts: [t('settings.security_settings.title'), t('password_confirmation_setting.title')], keywords: [t('password_confirmation_setting.subtitle')], highlightId: SettingsHighlightIds.PASSWORD_CONFIRMATION },
    ] },
  ] };
}

function getGeneralTab(routes: SettingsRoutes, t: T): TabGroup {
  return { tab: routes.SETTINGS_GENERAL, categories: [
    { categoryId: SettingsCategoryIds.GENERAL, children: [
      { texts: [t('general_settings.title')], keywords: [t('general_settings.subtitle')] },
      { texts: [t('general_settings.title'), t('general_settings.usage_analytics.title')], highlightId: SettingsHighlightIds.USAGE_ANALYTICS },
      { texts: [t('general_settings.title'), t('general_settings.auto_detect_tokens.title')], highlightId: SettingsHighlightIds.AUTO_DETECT_TOKENS },
      { texts: [t('general_settings.title'), t('general_settings.display_date_in_localtime.title')], highlightId: SettingsHighlightIds.DISPLAY_DATE_IN_LOCALTIME },
      { texts: [t('general_settings.title'), t('sync_indicator.setting.ask_user_upon_size_discrepancy.title')], highlightId: SettingsHighlightIds.ASK_SIZE_DISCREPANCY },
      { texts: [t('general_settings.title'), t('general_settings.version_update_check.title')], highlightId: SettingsHighlightIds.VERSION_UPDATE_CHECK },
      { texts: [t('general_settings.title'), t('general_settings.balance_frequency.title')], highlightId: SettingsHighlightIds.BALANCE_SAVE_FREQUENCY },
      { texts: [t('general_settings.title'), t('general_settings.labels.btc_derivation_gap')], highlightId: SettingsHighlightIds.BTC_DERIVATION_GAP },
      { texts: [t('general_settings.title'), t('date_format_help.title')], highlightId: SettingsHighlightIds.DATE_FORMAT },
    ] },
    { categoryId: SettingsCategoryIds.AMOUNT, children: [
      { texts: [t('general_settings.amount.title')], keywords: [t('general_settings.amount.subtitle')] },
      { texts: [t('general_settings.amount.title'), t('general_settings.amount.label.amount')], highlightId: SettingsHighlightIds.AMOUNT_FORMAT },
      { texts: [t('general_settings.amount.title'), t('rounding_settings.subscript.title')], keywords: [t('rounding_settings.subscript.subtitle')], highlightId: SettingsHighlightIds.SUBSCRIPT },
      { texts: [t('general_settings.amount.title'), t('rounding_settings.title')], keywords: [t('rounding_settings.subtitle')], highlightId: SettingsHighlightIds.ROUNDING },
      { texts: [t('general_settings.amount.title'), t('general_settings.amount.label.abbreviation')], highlightId: SettingsHighlightIds.ABBREVIATION },
      { texts: [t('general_settings.amount.title'), t('general_settings.amount.label.currency_location')], highlightId: SettingsHighlightIds.CURRENCY_LOCATION },
    ] },
    { categoryId: SettingsCategoryIds.NFT, children: [
      { texts: [t('general_settings.nft_setting.title')] },
      { texts: [t('general_settings.nft_setting.title'), t('general_settings.nft_setting.label.include_nfts_subtitle')], keywords: [t('general_settings.nft_setting.label.include_nfts_hint')], highlightId: SettingsHighlightIds.NFT_IN_NET_VALUE },
      { texts: [t('general_settings.nft_setting.title'), t('general_settings.nft_setting.subtitle.nft_images_rendering_setting')], keywords: [t('general_settings.nft_setting.subtitle.nft_images_rendering_setting_hint')], highlightId: SettingsHighlightIds.NFT_IMAGE_RENDERING },
    ] },
    { categoryId: SettingsCategoryIds.HISTORY_EVENT, children: [
      { texts: [t('general_settings.history_event.title')], keywords: [t('general_settings.history_event.subtitle')] },
      { texts: [t('general_settings.history_event.title'), t('general_settings.history_event.auto_create_profit_events.title')], highlightId: SettingsHighlightIds.AUTO_CREATE_PROFIT_EVENTS },
      { texts: [t('general_settings.history_event.title'), t('general_settings.history_event.internal_tx_conflicts.title')], highlightId: SettingsHighlightIds.INTERNAL_TX_CONFLICT_REPULL },
      { texts: [t('general_settings.history_event.title'), t('general_settings.history_event.skipped_events.title')], keywords: [t('general_settings.history_event.skipped_events.subtitle')], highlightId: SettingsHighlightIds.SKIPPED_EVENTS },
    ] },
    { categoryId: SettingsCategoryIds.EXTERNAL_SERVICE, children: [
      { texts: [t('general_settings.external_service_setting.title')], keywords: [t('general_settings.external_service_setting.subtitle')] },
      { texts: [t('general_settings.external_service_setting.title'), t('general_settings.external_service_setting.label.query_retry_limit')], keywords: [t('general_settings.external_service_setting.label.query_retry_limit_hint')], highlightId: SettingsHighlightIds.QUERY_RETRY_LIMIT },
      { texts: [t('general_settings.external_service_setting.title'), t('general_settings.external_service_setting.label.connect_timeout')], keywords: [t('general_settings.external_service_setting.label.connect_timeout_hint')], highlightId: SettingsHighlightIds.CONNECT_TIMEOUT },
      { texts: [t('general_settings.external_service_setting.title'), t('general_settings.external_service_setting.label.read_timeout')], keywords: [t('general_settings.external_service_setting.label.read_timeout_hint')], highlightId: SettingsHighlightIds.READ_TIMEOUT },
      { texts: [t('general_settings.external_service_setting.title'), t('general_settings.external_service_setting.suppress_missing_key.title')], keywords: [t('general_settings.external_service_setting.suppress_missing_key.subtitle')], highlightId: SettingsHighlightIds.SUPPRESS_MISSING_KEY },
    ] },
    { categoryId: SettingsCategoryIds.BACKEND, children: [
      { texts: [t('backend_settings.title')], keywords: [t('backend_settings.subtitle')] },
      { texts: [t('backend_settings.title'), t('backend_settings.settings.log_level.label')], keywords: [t('backend_settings.settings.log_level.hint')], highlightId: SettingsHighlightIds.LOG_LEVEL },
    ] },
  ] };
}

function getDatabaseTab(routes: SettingsRoutes, t: T): TabGroup {
  return { tab: routes.SETTINGS_DATABASE, categories: [
    { categoryId: SettingsCategoryIds.DATABASE_INFO, children: [
      { texts: [t('database_settings.database_info.title')], keywords: [t('database_settings.database_info.subtitle')] },
      { texts: [t('database_settings.database_info.title'), t('database_settings.database_info.labels.userdb')], highlightId: SettingsHighlightIds.USERDB_INFO },
      { texts: [t('database_settings.database_info.title'), t('database_settings.database_info.labels.globaldb')], highlightId: SettingsHighlightIds.GLOBALDB_INFO },
    ] },
    { categoryId: SettingsCategoryIds.USER_BACKUPS, children: [
      { texts: [t('database_settings.user_backups.title')], keywords: [t('database_settings.user_backups.subtitle')] },
    ] },
    { categoryId: SettingsCategoryIds.MANAGE_DATA, children: [
      { texts: [t('database_settings.manage_data.title')], keywords: [t('database_settings.manage_data.subtitle')] },
      { texts: [t('database_settings.manage_data.title'), t('data_management.purge_data.title')], keywords: [t('data_management.purge_data.subtitle')], highlightId: SettingsHighlightIds.PURGE_DATA },
      { texts: [t('database_settings.manage_data.title'), t('data_management.purge_images_cache.title')], keywords: [t('data_management.purge_images_cache.subtitle')], highlightId: SettingsHighlightIds.PURGE_IMAGES_CACHE },
      { texts: [t('database_settings.manage_data.title'), t('data_management.refresh_cache.title')], keywords: [t('data_management.refresh_cache.subtitle')], highlightId: SettingsHighlightIds.REFRESH_CACHE },
    ] },
    { categoryId: SettingsCategoryIds.IMPORT_EXPORT, children: [
      { texts: [t('database_settings.import_export.title')], keywords: [t('database_settings.import_export.subtitle')] },
    ] },
    { categoryId: SettingsCategoryIds.ASSET_DATABASE, children: [
      { texts: [t('database_settings.asset_database.title')], keywords: [t('database_settings.asset_database.subtitle')] },
      { texts: [t('database_settings.asset_database.title'), t('asset_update.manual.title')], keywords: [t('asset_update.manual.subtitle')], highlightId: SettingsHighlightIds.ASSET_UPDATE },
      { texts: [t('database_settings.asset_database.title'), t('asset_update.restore.title')], keywords: [t('asset_update.restore.subtitle')], highlightId: SettingsHighlightIds.RESTORE_ASSETS_DB },
    ] },
  ] };
}

function getAccountingTab(routes: SettingsRoutes, t: T): TabGroup {
  return { tab: routes.SETTINGS_ACCOUNTING, categories: [
    { children: [
      { texts: [t('accounting_settings.rule.title')], keywords: [t('accounting_settings.rule.subtitle')], highlightId: SettingsHighlightIds.ACCOUNTING_RULE },
      { texts: [t('accounting_settings.trade.title')], highlightId: SettingsHighlightIds.ACCOUNTING_TRADE, keywords: [
        t('accounting_settings.trade.labels.include_crypto2crypto'),
        t('accounting_settings.trade.labels.include_gas_costs'),
        t('accounting_settings.trade.labels.tax_free'),
        t('accounting_settings.trade.labels.calculate_past_cost_basis'),
        t('accounting_settings.trade.labels.include_fees_in_cost_basis'),
        t('accounting_settings.trade.labels.cost_basis_method'),
        t('accounting_settings.trade.labels.eth_staking_taxable_after_withdrawal_enabled'),
      ] },
      { texts: [t('account_settings.csv_export_settings.title')], highlightId: SettingsHighlightIds.CSV_EXPORT },
    ] },
  ] };
}

function getEvmTab(routes: SettingsRoutes, t: T): TabGroup {
  return { tab: routes.SETTINGS_EVM, categories: [
    { categoryId: SettingsCategoryIds.CHAINS, children: [
      { texts: [t('evm_settings.general.title')] },
      { texts: [t('evm_settings.general.title'), t('evm_settings.general.treat_eth2_as_eth.title')], keywords: [t('evm_settings.general.treat_eth2_as_eth.subtitle')], highlightId: SettingsHighlightIds.TREAT_ETH2_AS_ETH },
      { texts: [t('evm_settings.general.title'), t('evm_settings.general.chains_to_skip_detection.title')], keywords: [t('evm_settings.general.chains_to_skip_detection.subtitle')], highlightId: SettingsHighlightIds.CHAINS_TO_SKIP_DETECTION },
    ] },
    { categoryId: SettingsCategoryIds.INDEXER, children: [
      { texts: [t('evm_settings.indexer.title')], keywords: [t('evm_settings.indexer.subtitle')] },
    ] },
  ] };
}

function getOracleTab(routes: SettingsRoutes, t: T): TabGroup {
  return { tab: routes.SETTINGS_ORACLE, categories: [
    { categoryId: SettingsCategoryIds.PRICE_ORACLE, children: [
      { texts: [t('price_oracle_settings.title')], keywords: [t('price_oracle_settings.subtitle')] },
      { texts: [t('price_oracle_settings.title'), t('price_oracle_settings.latest_prices')] },
      { texts: [t('price_oracle_settings.title'), t('price_oracle_settings.historic_prices')] },
    ] },
    { categoryId: SettingsCategoryIds.PENALTY, children: [
      { texts: [t('oracle_cache_management.penalty.title')], keywords: [t('oracle_cache_management.penalty.subtitle')] },
      { texts: [t('oracle_cache_management.penalty.title'), t('oracle_cache_management.penalty.labels.oracle_penalty_duration')], highlightId: SettingsHighlightIds.ORACLE_PENALTY_DURATION },
      { texts: [t('oracle_cache_management.penalty.title'), t('oracle_cache_management.penalty.labels.oracle_penalty_threshold_count')], highlightId: SettingsHighlightIds.ORACLE_PENALTY_THRESHOLD },
    ] },
  ] };
}

function getRpcTab(routes: SettingsRoutes, t: T): TabGroup {
  return { tab: routes.SETTINGS_RPC, categories: [
    { children: [
      { texts: [t('general_settings.rpc_node_setting.title')], highlightId: SettingsHighlightIds.RPC_NODES, keywords: [t('general_settings.rpc_node_setting.subtitle')] },
    ] },
  ] };
}

function getModulesTab(routes: SettingsRoutes, t: T): TabGroup {
  return { tab: routes.SETTINGS_MODULES, categories: [
    { children: [
      { texts: [t('module_settings.title')], highlightId: SettingsHighlightIds.MODULES, keywords: [t('module_settings.subtitle')] },
    ] },
  ] };
}

function getInterfaceTab(routes: SettingsRoutes, t: T): TabGroup {
  return { tab: routes.SETTINGS_INTERFACE, categories: [
    { categoryId: SettingsCategoryIds.INTERFACE_ONLY, children: [
      { texts: [t('frontend_settings.title')] },
      { texts: [t('general_settings.language.title')], keywords: [t('general_settings.language.subtitle')], highlightId: SettingsHighlightIds.LANGUAGE },
      { texts: [t('frontend_settings.animations.title')], highlightId: SettingsHighlightIds.ANIMATIONS },
      { texts: [t('frontend_settings.persist_table_sorting.title')], keywords: [t('frontend_settings.persist_table_sorting.subtitle')], highlightId: SettingsHighlightIds.PERSIST_TABLE_SORTING },
      { texts: [t('frontend_settings.scramble.title')], highlightId: SettingsHighlightIds.SCRAMBLE },
      { texts: [t('frontend_settings.persist_privacy.title')], highlightId: SettingsHighlightIds.PERSIST_PRIVACY },
      { texts: [t('frontend_settings.refresh_balance.title')], highlightId: SettingsHighlightIds.REFRESH_BALANCE },
      { texts: [t('frontend_settings.periodic_query.title')], highlightId: SettingsHighlightIds.PERIODIC_QUERY },
      { texts: [t('explorers.title')], keywords: [t('explorers.subtitle')], highlightId: SettingsHighlightIds.EXPLORERS },
      { texts: [t('frontend_settings.history_query_indicator.title')] },
      { texts: [t('frontend_settings.history_query_indicator.title'), t('frontend_settings.history_query_indicator.min_out_of_sync_period.title')], keywords: [t('frontend_settings.history_query_indicator.min_out_of_sync_period.subtitle')], highlightId: SettingsHighlightIds.MIN_OUT_OF_SYNC_PERIOD },
      { texts: [t('frontend_settings.history_query_indicator.title'), t('frontend_settings.history_query_indicator.dismissal_threshold.title')], keywords: [t('frontend_settings.history_query_indicator.dismissal_threshold.subtitle')], highlightId: SettingsHighlightIds.DISMISSAL_THRESHOLD },
      { texts: [t('frontend_settings.history_query_indicator.title'), t('frontend_settings.history_query_indicator.reset_dismissal_status.title')], keywords: [t('frontend_settings.history_query_indicator.reset_dismissal_status.subtitle')], highlightId: SettingsHighlightIds.RESET_DISMISSAL_STATUS },
    ] },
    { categoryId: SettingsCategoryIds.GRAPH, children: [
      { texts: [t('frontend_settings.subtitle.graph_settings')], keywords: [t('frontend_settings.subtitle.graph_settings_hint')] },
      { texts: [t('frontend_settings.subtitle.graph_settings'), t('timeframe_settings.default_timeframe')], keywords: [t('timeframe_settings.default_timeframe_description')], highlightId: SettingsHighlightIds.TIMEFRAME },
      { texts: [t('frontend_settings.subtitle.graph_settings'), t('frontend_settings.graph_basis.title')], highlightId: SettingsHighlightIds.GRAPH_BASIS },
    ] },
    { categoryId: SettingsCategoryIds.ALIAS, children: [
      { texts: [t('frontend_settings.subtitle.alias_names')] },
    ] },
    { categoryId: SettingsCategoryIds.NEWLY_DETECTED_TOKENS, children: [
      { texts: [t('frontend_settings.newly_detected_tokens.title')], keywords: [t('frontend_settings.newly_detected_tokens.subtitle')] },
      { texts: [t('frontend_settings.newly_detected_tokens.title'), t('frontend_settings.newly_detected_tokens.max_count.title')], highlightId: SettingsHighlightIds.NEWLY_DETECTED_TOKENS_MAX_COUNT },
      { texts: [t('frontend_settings.newly_detected_tokens.title'), t('frontend_settings.newly_detected_tokens.ttl_days.title')], highlightId: SettingsHighlightIds.NEWLY_DETECTED_TOKENS_TTL },
    ] },
    { categoryId: SettingsCategoryIds.THEME, children: [
      { texts: [t('premium_components.theme_manager.text')], keywords: [t('premium_components.theme_manager.text_hint')] },
    ] },
  ] };
}

export function useSettingsSearch(): UseSettingsSearchReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { appRoutes } = useAppRoutes();

  const entries = computed<SettingsSearchEntry[]>(() => {
    const routes = get(appRoutes);

    const tabs: TabGroup[] = [
      getAccountTab(routes, t),
      getGeneralTab(routes, t),
      getDatabaseTab(routes, t),
      getAccountingTab(routes, t),
      getEvmTab(routes, t),
      getOracleTab(routes, t),
      getRpcTab(routes, t),
      getModulesTab(routes, t),
      getInterfaceTab(routes, t),
    ];

    return tabs.flatMap(({ tab, categories }: TabGroup) =>
      categories.flatMap(({ categoryId, children }: CategoryDef) =>
        children.map(({ texts, keywords, highlightId }: EntryDef) => ({
          categoryId,
          highlightId,
          icon: tab.icon,
          keywords,
          route: tab.route,
          texts: [tab.text, ...texts],
        })),
      ),
    );
  });

  function getSearchToken(e: SettingsSearchEntry): string {
    return getTextToken([...e.texts, ...(e.keywords ?? [])].join(' '));
  }

  function filterEntries(entries: SettingsSearchEntry[], keyword: string): SettingsSearchEntry[] {
    const words: string[] = keyword.split(/\s+/).map((w: string) => getTextToken(w)).filter(Boolean);
    const scored: { entry: SettingsSearchEntry; points: number }[] = entries.map((e: SettingsSearchEntry) => {
      let points: number = 0;
      const text: string = getSearchToken(e);
      for (const word of words) {
        const idx: number = text.indexOf(word);
        if (idx > -1) {
          points++;
          if (idx === 0)
            points += 0.5;
        }
      }
      return { entry: e, points };
    });
    return scored
      .filter(s => s.points > 0)
      .sort((a, b) => b.points - a.points)
      .map(s => s.entry);
  }

  return {
    entries,
    filterEntries,
  };
}
