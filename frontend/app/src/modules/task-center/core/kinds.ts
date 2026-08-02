import { type Activity, type ActivityKind, ActivityKind as Kind, type TranslateFn } from './types';

interface KindDescriptor {
  kind: ActivityKind;
  /** Static i18n key only (no dynamic keys — see CLAUDE.md). */
  groupTitle: (t: TranslateFn) => string;
}

/**
 * The single source of truth for kind ordering and group titles. Array order is the display +
 * selection priority (highest first): it drives group ordering and which running activity the
 * header bar labels (`current`). Adding a kind is one entry here (plus the enum) — there is no
 * separate priority list to keep in sync.
 *
 * Kinds that never produce an activity (deferred: db-upgrade/data-migration) are intentionally
 * omitted; they rank last via {@link kindRank} and never appear.
 */
const KINDS: readonly KindDescriptor[] = [
  { groupTitle: t => t('task_center.group.blockchain_balances'), kind: Kind.BLOCKCHAIN_BALANCES },
  { groupTitle: t => t('task_center.group.accounts'), kind: Kind.ACCOUNTS },
  { groupTitle: t => t('task_center.group.all_balances'), kind: Kind.ALL_BALANCES },
  { groupTitle: t => t('task_center.group.manual_balances'), kind: Kind.MANUAL_BALANCES },
  { groupTitle: t => t('task_center.group.nft_balances'), kind: Kind.NFT_BALANCES },
  { groupTitle: t => t('task_center.group.token_detection'), kind: Kind.TOKEN_DETECTION },
  { groupTitle: t => t('task_center.group.exchange_balances'), kind: Kind.EXCHANGE_BALANCES },
  { groupTitle: t => t('task_center.group.staking'), kind: Kind.STAKING },
  { groupTitle: t => t('task_center.group.history_sync'), kind: Kind.HISTORY_SYNC },
  { groupTitle: t => t('task_center.group.purge'), kind: Kind.PURGE },
  { groupTitle: t => t('task_center.group.tx_sync'), kind: Kind.TX_SYNC },
  { groupTitle: t => t('task_center.group.tx_decoding'), kind: Kind.TX_DECODING },
  { groupTitle: t => t('task_center.group.redecode'), kind: Kind.REDECODE },
  { groupTitle: t => t('task_center.group.eth_block_decoding'), kind: Kind.ETH_BLOCK_DECODING },
  { groupTitle: t => t('task_center.group.repulling'), kind: Kind.REPULLING },
  { groupTitle: t => t('task_center.group.exchange_events'), kind: Kind.EXCHANGE_EVENTS },
  { groupTitle: t => t('task_center.group.online_events'), kind: Kind.ONLINE_EVENTS },
  { groupTitle: t => t('task_center.group.history_events'), kind: Kind.HISTORY_EVENTS },
  { groupTitle: t => t('task_center.group.protocol_cache'), kind: Kind.PROTOCOL_CACHE },
  { groupTitle: t => t('task_center.group.sync'), kind: Kind.SYNC },
  { groupTitle: t => t('task_center.group.gnosis_pay'), kind: Kind.GNOSIS_PAY },
  { groupTitle: t => t('task_center.group.liquidity_pools'), kind: Kind.LIQUIDITY_POOLS },
  { groupTitle: t => t('task_center.group.liquity'), kind: Kind.LIQUITY },
  { groupTitle: t => t('task_center.group.prices'), kind: Kind.PRICES },
  { groupTitle: t => t('task_center.group.pnl_report'), kind: Kind.PNL_REPORT },
  { groupTitle: t => t('task_center.group.historical_balances'), kind: Kind.HISTORICAL_BALANCES },
  { groupTitle: t => t('task_center.group.assets'), kind: Kind.ASSETS },
  { groupTitle: t => t('task_center.group.accounting_rules'), kind: Kind.ACCOUNTING_RULES },
  { groupTitle: t => t('task_center.group.airdrops'), kind: Kind.AIRDROPS },
  { groupTitle: t => t('task_center.group.csv_import'), kind: Kind.CSV_IMPORT },
  { groupTitle: t => t('task_center.group.other'), kind: Kind.OTHER },
];

const KIND_ORDER: readonly ActivityKind[] = KINDS.map(descriptor => descriptor.kind);
const GROUP_TITLE = new Map(KINDS.map(descriptor => [descriptor.kind, descriptor.groupTitle]));

/** Priority rank of a kind (lower = higher priority); unranked kinds sort last. */
export function kindRank(kind: ActivityKind): number {
  const index = KIND_ORDER.indexOf(kind);
  return index === -1 ? KIND_ORDER.length : index;
}

/** Localized group title for a kind; falls back to the first activity's title. */
export function groupTitle(kind: ActivityKind, activities: Activity[], t: TranslateFn): string {
  return GROUP_TITLE.get(kind)?.(t) ?? activities[0]?.title ?? kind;
}
