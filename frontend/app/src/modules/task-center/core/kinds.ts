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
  { groupTitle: t => t('task_center.group.bank_balances'), kind: Kind.BANK_BALANCES },
  { groupTitle: t => t('task_center.group.staking'), kind: Kind.STAKING },
  { groupTitle: t => t('task_center.group.history_sync'), kind: Kind.HISTORY_SYNC },
  { groupTitle: t => t('task_center.group.purge'), kind: Kind.PURGE },
  { groupTitle: t => t('task_center.group.tx_sync'), kind: Kind.TX_SYNC },
  { groupTitle: t => t('task_center.group.tx_decoding'), kind: Kind.TX_DECODING },
  { groupTitle: t => t('task_center.group.redecode'), kind: Kind.REDECODE },
  { groupTitle: t => t('task_center.group.eth_block_decoding'), kind: Kind.ETH_BLOCK_DECODING },
  { groupTitle: t => t('task_center.group.repulling'), kind: Kind.REPULLING },
  { groupTitle: t => t('task_center.group.exchange_events'), kind: Kind.EXCHANGE_EVENTS },
  { groupTitle: t => t('task_center.group.bank_events'), kind: Kind.BANK_EVENTS },
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

/**
 * The kinds the dock's pill names, in the order it picks between them.
 *
 * @remarks
 * Ranked by the data a user opens the app to look at, not by how long the work takes. Upkeep that
 * only feeds that data (prices, the protocol cache, block decoding, token detection) is left out, so
 * it adds to "+N more" and never becomes the caption while one of these runs.
 *
 * Separate from {@link KINDS}, whose order drives the panel's groups. Progress units differ between
 * these kinds (leaves for a history refresh, events for historical balances), so the pill shows one
 * job's count rather than adding them up.
 */
const GLOBAL_KINDS: readonly ActivityKind[] = [
  Kind.HISTORY_SYNC,
  Kind.REDECODE,
  Kind.REPULLING,
  Kind.ALL_BALANCES,
  Kind.BLOCKCHAIN_BALANCES,
  Kind.EXCHANGE_BALANCES,
  Kind.BANK_BALANCES,
  Kind.HISTORICAL_BALANCES,
  Kind.PNL_REPORT,
  Kind.CSV_IMPORT,
];

/** Where a kind ranks among the kinds the pill names (lower first), or `undefined` for one it never names. */
export function globalKindRank(kind: ActivityKind): number | undefined {
  const index = GLOBAL_KINDS.indexOf(kind);
  return index === -1 ? undefined : index;
}

/**
 * The kinds a bulk stop may interrupt: every producer of them only reads, syncs or rebuilds a cache,
 * so stopping one leaves the data as it was before it started, and running it again finishes it.
 *
 * @remarks
 * Chosen per kind, so a kind is only here when all of its producers are safe. `PRICES` is left out
 * because it also saves and removes manual prices, `PNL_REPORT` because it also imports report
 * data, `STAKING` because it also adds validators, and `MANUAL_BALANCES` because it also saves them.
 * Work that deletes before it re-derives declares `resets`, which excludes it whatever its kind.
 */
const SAFE_TO_STOP_KINDS: ReadonlySet<ActivityKind> = new Set([
  Kind.ALL_BALANCES,
  Kind.BLOCKCHAIN_BALANCES,
  Kind.EXCHANGE_BALANCES,
  Kind.BANK_BALANCES,
  Kind.NFT_BALANCES,
  Kind.EXCHANGE_SAVINGS,
  Kind.TOKEN_DETECTION,
  Kind.HISTORY_SYNC,
  Kind.TX_SYNC,
  Kind.TX_DECODING,
  Kind.ETH_BLOCK_DECODING,
  Kind.EXCHANGE_EVENTS,
  Kind.BANK_EVENTS,
  Kind.ONLINE_EVENTS,
  Kind.PROTOCOL_CACHE,
  Kind.HISTORICAL_BALANCES,
  Kind.LIQUIDITY_POOLS,
  Kind.LIQUITY,
  Kind.AIRDROPS,
]);

/** Whether a bulk stop may interrupt work of this kind. See {@link SAFE_TO_STOP_KINDS}. */
export function isSafeToStop(kind: ActivityKind): boolean {
  return SAFE_TO_STOP_KINDS.has(kind);
}

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
