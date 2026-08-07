import type { MessageKey } from '@/message-key';
import { type Brand, make } from 'plainfp/brand';

/**
 * Injected translator. The pure core never calls `useI18n`; the reactive shell passes the
 * real `t`, specs pass a fake one. Keeps every adapter and the assembler unit-testable with
 * literal inputs.
 */
export type TranslateFn = (key: string, params?: Record<string, unknown>, plural?: number) => string;

/**
 * A label that is not yet a string. Producers build these; the render layer resolves them with its
 * own `t`, so a language change updates work that is already in flight rather than freezing the
 * wording chosen at submit time.
 *
 * The key is branded: only `msg.$t('literal')` produces a {@link MessageKey}, which is also what
 * makes the i18n key-usage lint rules count a key referenced solely from a config table as used.
 * The import is type-only, so this file still pulls no i18n machinery into the pure core.
 */
export interface TranslatableText {
  readonly key: MessageKey;
  readonly params?: Record<string, unknown>;
  /** vue-i18n pluralization choice, passed through as `t(key, params, plural)`. */
  readonly plural?: number;
}

/**
 * A subtitle is either a value the producer already formatted (a chain name, an address, a tx
 * hash) or a description that has to be translated where it is rendered. Values stay plain
 * strings: they carry no translatable text, only data.
 */
export type ActivityText = string | TranslatableText;

/** Resolves an {@link ActivityText} for display. Pure: the caller injects its own `t`. */
export function resolveText(t: TranslateFn, value: ActivityText | undefined): string | undefined {
  if (value === undefined || typeof value === 'string')
    return value;

  return value.plural === undefined
    ? t(value.key, value.params)
    : t(value.key, value.params ?? {}, value.plural);
}

/**
 * Deterministic identity for an activity. Always derived from its source
 * (`${kind}:${...parts}`), never random — see {@link makeActivityId}. A stable id keeps Vue
 * `:key`s stable, makes deduplication free (same work → same id) and lets the controller
 * target an item.
 */
export type ActivityId = Brand<string, 'ActivityId'>;

/** Identity of a cancellable group of activities (e.g. a batch of tx queries — issue #10955). */
export type GroupId = Brand<string, 'GroupId'>;

/**
 * The category of long-running work an activity represents. Enumerified as `const` so there
 * are no magic strings at any call site.
 */
export const ActivityKind = {
  BLOCKCHAIN_BALANCES: 'blockchain-balances',
  ACCOUNTS: 'accounts',
  ALL_BALANCES: 'all-balances',
  MANUAL_BALANCES: 'manual-balances',
  NFT_BALANCES: 'nft-balances',
  EXCHANGE_BALANCES: 'exchange-balances',
  EXCHANGE_SAVINGS: 'exchange-savings',
  TOKEN_DETECTION: 'token-detection',
  /** The umbrella for a whole history refresh; its children are the per-chain and per-account work. */
  HISTORY_SYNC: 'history-sync',
  /** Deleting cached data for one purgeable source; what derives from it declares `staleAfter`. */
  PURGE: 'purge',
  /**
   * Turning one module on or off. Ephemeral — it exists so what a module feeds can declare a
   * `staleAfter` edge against it, not to be shown as work.
   */
  MODULE_TOGGLE: 'module-toggle',
  TX_SYNC: 'tx-sync',
  TX_DECODING: 'tx-decoding',
  /** A user-triggered flow that re-derives events; its children are the per-chain decodes. */
  REDECODE: 'redecode',
  ETH_BLOCK_DECODING: 'eth-block-decoding',
  REPULLING: 'repulling',
  EXCHANGE_EVENTS: 'exchange-events',
  ONLINE_EVENTS: 'online-events',
  PROTOCOL_CACHE: 'protocol-cache',
  SYNC: 'sync',
  GNOSIS_PAY: 'gnosis-pay',
  LIQUIDITY_POOLS: 'liquidity-pools',
  LIQUITY: 'liquity',
  HISTORY_EVENTS: 'history-events',
  PRICES: 'prices',
  STAKING: 'staking',
  HISTORICAL_BALANCES: 'historical-balances',
  PNL_REPORT: 'pnl-report',
  ASSETS: 'assets',
  ACCOUNTING_RULES: 'accounting-rules',
  AIRDROPS: 'airdrops',
  CSV_IMPORT: 'csv-import',
  DB_UPGRADE: 'db-upgrade',
  DATA_MIGRATION: 'data-migration',
  // Pre-login unlock work (login / account creation). Runs through the orchestrator like any
  // other activity but is flagged {@link ActivitySpec.ephemeral}, so it never surfaces in the
  // task center. Kept out of the `kinds.ts` display table for the same reason.
  SESSION: 'session',
  OTHER: 'other',
} as const;

export type ActivityKind = (typeof ActivityKind)[keyof typeof ActivityKind];

/**
 * Model-facing status. The orchestrator's internal queued state projects to {@link PENDING};
 * the model never needs a separate "queued" — pending *is* "waiting to start".
 */
export const ActivityStatus = {
  PENDING: 'pending',
  RUNNING: 'running',
  COMPLETE: 'complete',
  CANCELLED: 'cancelled',
  FAILED: 'failed',
  /** Deliberately not run — the user configured this work off. Terminal, but not a success. */
  SKIPPED: 'skipped',
} as const;

export type ActivityStatus = (typeof ActivityStatus)[keyof typeof ActivityStatus];

export const ActivityPhase = {
  IDLE: 'idle',
  WORKING: 'working',
  DONE: 'done',
} as const;

export type ActivityPhase = (typeof ActivityPhase)[keyof typeof ActivityPhase];

/**
 * Discriminant for {@link ActivitySource}. Kept as a tagged union of one so the render model and
 * the controller stay open to a second kind of work without reshaping every activity.
 */
export const ActivitySourceType = {
  NATIVE: 'native',
} as const;

export type ActivitySourceType = (typeof ActivitySourceType)[keyof typeof ActivitySourceType];

/**
 * Carries what the controller needs to cancel/re-run an item. Every activity is owned by the
 * orchestrator, which addresses it by id, so the source only has to identify itself.
 *
 * A `BACKEND_TASK` arm existed while the floor surfaced un-migrated backend tasks; it went with
 * the floor once every producer was native. Seven further arms (TX_SYNC, DECODING,
 * EXCHANGE_EVENTS, PROTOCOL_CACHE, BALANCE_QUERY, REQUEST_TAG, INFO) were declared for a
 * per-producer routing scheme that native migration made unnecessary, and were deleted in W0.
 */
export interface ActivitySource {
  type: typeof ActivitySourceType.NATIVE;
}

/** Naive, step-based progress — the model already used by PnL and db-upgrade UIs. */
export interface ActivitySteps {
  current: number;
  total: number;
}

export interface Activity {
  readonly id: ActivityId;
  readonly kind: ActivityKind;
  /** Optional grouping for batch control (cancel-all-in-group, issue #10955). */
  readonly group?: GroupId;
  /**
   * The activity this one is a part of, when a producer submits its work as a tree
   * (see {@link ActivitySpec.parent}). Descriptive only — scheduling is `deps` plus the lane caps.
   */
  readonly parent?: ActivityId;
  /** i18n, human readable. */
  readonly title: string;
  /** Optional context, e.g. chain / address / location. See {@link ActivityText}. */
  readonly subtitle?: ActivityText;
  readonly status: ActivityStatus;
  readonly steps?: ActivitySteps;
  /** Derived 0-100; `-1` for indeterminate kinds. */
  readonly percentage: number;
  /** Whether the controller knows how to cancel this item. */
  readonly cancellable: boolean;
  readonly rerunnable: boolean;
  readonly source: ActivitySource;
  readonly startedAt?: number;
  /**
   * Excluded from the task-center render model (see {@link ActivitySpec.ephemeral}). The
   * orchestrator still tracks it internally; only the reactive projection drops it, so pre-login
   * unlock work runs through the same spine without ever showing as an activity.
   */
  readonly ephemeral?: boolean;
  /**
   * Whether this activity deletes data before re-deriving it. Read by the eligibility rules to keep
   * a reset from overlapping work that writes to the same rows — the one overlap that is not merely
   * duplicate effort. See {@link HistoryFlow.resets}, which is where a flow declares it.
   */
  readonly resets?: boolean;
}

export interface ActivityGroup {
  readonly kind: ActivityKind;
  readonly title: string;
  readonly activities: Activity[];
  /** Rolled up from {@link activities}. */
  readonly status: ActivityStatus;
  /** Rolled up 0-100; `-1` when indeterminate. */
  readonly percentage: number;
}

export interface ActivityOverall {
  readonly percentage: number;
  readonly phase: ActivityPhase;
}

export interface ActivityModel {
  readonly groups: ActivityGroup[];
  /** Flat, currently running. */
  readonly active: Activity[];
  /** Flat, waiting to start. */
  readonly pending: Activity[];
  /**
   * The tops of the activity tree — what a user actually started, as opposed to the work it fanned
   * out into. See {@link ./tree}; `children` holds the rest, keyed by parent id.
   */
  readonly roots: Activity[];
  readonly children: ReadonlyMap<ActivityId, Activity[]>;
  readonly overall: ActivityOverall;
  /** The single activity the header bar labels; see selection rule in {@link ./model}. */
  readonly current?: Activity;
}

/**
 * What the work-history remembers about one settled activity, keyed by its {@link ActivityId}
 * and overwritten on each settle. Tiny and durable: it survives `clearTerminal` so the
 * orchestrator can answer "did this ever load, and when" — the freshness half of the old
 * status store. `lastSuccessAt` is set only on a successful completion, so a later failure
 * never erases the fact that data was once loaded.
 */
export interface CompletionRecord {
  readonly kind: ActivityKind;
  readonly lastOutcome: ActivityStatus;
  readonly lastSettledAt: number;
  readonly lastSuccessAt?: number;
}

/**
 * The projected status of a kind (or a specific id) — the single replacement for
 * `useStatusUpdater`. Liveness (`running`/`pending`/`active`) comes from the live records;
 * freshness (`everCompleted`/`lastCompletedAt`) from the completion ledger.
 */
export interface WorkStatus {
  readonly running: boolean;
  readonly pending: boolean;
  /** `running || pending` — the replacement for `loading()`. */
  readonly active: boolean;
  /** A success has been recorded — the inverse of `isFirstLoad()`. */
  readonly everCompleted: boolean;
  /** Epoch ms of the last success; feeds a TTL refresh-gate. */
  readonly lastCompletedAt?: number;
  /** The most recent terminal outcome, even if it was a failure over stale-but-present data. */
  readonly lastOutcome?: ActivityStatus;
}

/**
 * Static discriminator parts for {@link makeActivityId} — the fixed sub-identity facets that
 * separate variants of one {@link ActivityKind} (e.g. cached vs network balances, generate vs
 * export of a report). Dynamic facets (chain, address, location) stay raw values; only these
 * fixed strings are enumerified so call sites never repeat a magic string.
 */
export const ActivityPart = {
  CACHED: 'cached',
  PULL: 'pull',
  /**
   * The umbrella over a fan-out, as opposed to one subject's own work. Keeps a run's id
   * (`…:run:<scope>:<mode>`) from ever colliding with a subject's (`…:<chain>`).
   */
  RUN: 'run',
  EXPORT: 'export',
  EXCHANGE_RATES: 'exchange-rates',
  ORACLE_CACHE: 'oracle-cache',
  /** The latest-price sweep, as opposed to historic/daily/exchange-rate price work. */
  LATEST: 'latest',
  /**
   * A user editing prices by hand, as opposed to the app fetching them. Its own parent so a
   * consumer can declare itself stale after a manual edit (`prices:manual:*`) without also
   * matching every automatic sweep — `staleAfter` matches by id *prefix*.
   */
  MANUAL: 'manual',
  HISTORIC: 'historic',
  DAILY: 'daily',
  BATCH: 'batch',
  UNISWAP_V2: 'uniswap-v2',
  SUSHISWAP: 'sushiswap',
  FETCH: 'fetch',
  ADD: 'add',
  /**
   * Work scoped to an account *category* ("every EVM chain") rather than a chain. A literal part
   * rather than a bare category name, so such an id can never be mistaken for a chain-scoped one
   * by a prefix reader — a chain would have to be named `category` for them to overlap.
   */
  CATEGORY: 'category',
  EDIT: 'edit',
  PERFORMANCE: 'performance',
  VALIDATORS: 'validators',
  KRAKEN: 'kraken',
  BALANCES: 'balances',
  POOLS: 'pools',
  STATISTICS: 'statistics',
  // The Liquity staking variant. A *part* named `staking` under the `LIQUITY` kind
  // (`liquity:staking`); unrelated to the `STAKING` *kind* — parts and kinds are separate keyspaces.
  STAKING: 'staking',
  ERC20: 'erc20',
  VERSIONS: 'versions',
  UPDATE: 'update',
  IMPORT: 'import',
  RESET: 'reset',
  NFTS: 'nfts',
  UNDECODED: 'undecoded',
  /**
   * What a re-pull is re-pulling. `REPULLING` covers three separate backend operations, so the
   * kind alone is not an identity — see the ids in `use-history-transactions.ts`.
   */
  TRANSACTIONS: 'transactions',
  EXCHANGE_EVENTS: 'exchange-events',
  MATCH: 'match',
  BRIDGE: 'bridge',
  LOOKUP: 'lookup',
  SERIES: 'series',
  DIVERGENCE: 'divergence',
  REMOVE: 'remove',
  DETECT: 'detect',
  ENS: 'ens',
  NONCE: 'nonce',
  VERIFY: 'verify',
  LOGIN: 'login',
  CREATE: 'create',
  // Scope facets: whether a flow covers everything or an explicit subset. The subset's members stay
  // raw values appended after `CHAINS`.
  ALL: 'all',
  CHAINS: 'chains',
  /**
   * A request naming the individual transactions and block events it covers, rather than a chain
   * or the whole set. The members stay raw values appended after this, as with `CHAINS`.
   */
  TARGETED: 'targeted',
} as const;

export type ActivityPart = (typeof ActivityPart)[keyof typeof ActivityPart];

const ID_SEPARATOR = ':';

/**
 * Builds a deterministic {@link ActivityId} from a kind and the parts that make the
 * underlying work unique (e.g. chain, address). The same work always yields the same id,
 * which is what makes dedup and stable rendering work.
 */
export function makeActivityId(kind: ActivityKind, ...keyParts: (string | number)[]): ActivityId {
  return make<string, 'ActivityId'>([kind, ...keyParts].join(ID_SEPARATOR));
}

/**
 * The inverse of {@link makeActivityId}: the key parts that followed the kind, in order. Lets a
 * reader recover the structured identity (chain, address, …) an activity was built from without
 * threading a separate source object through the orchestrator. Returns `[]` for a kind-only id.
 */
export function activityParts(id: ActivityId): string[] {
  return id.split(ID_SEPARATOR).slice(1);
}

/**
 * True when `id` is `makeActivityId(kind, ...parts)` itself or one of its descendants — i.e. an
 * id built from the same kind and leading parts plus further ones.
 *
 * This is what lets a producer keep a *per-request* identity while a reader still asks a coarse
 * question. Historic prices submit one activity per `(fromAsset, toAsset, timestamp)`, so their
 * ids must differ or `submitTask` would dedup two distinct queries onto one promise; but the
 * spinner sites only care whether *any* historic fetch is in flight. Exact-id matching can't
 * express that, and whole-kind aggregation is too coarse (PRICES also covers latest prices,
 * exchange rates and the oracle cache).
 *
 * Matches on a separator boundary, so `prices:historic` does not match `prices:historical-x`.
 */
export function activityIdHasPrefix(id: ActivityId, kind: ActivityKind, ...parts: (string | number)[]): boolean {
  const prefix = makeActivityId(kind, ...parts);
  return id === prefix || id.startsWith(prefix + ID_SEPARATOR);
}

/** Builds a deterministic {@link GroupId} from the parts that identify a cancellable batch. */
export function makeGroupId(...keyParts: (string | number)[]): GroupId {
  return make<string, 'GroupId'>(keyParts.join(ID_SEPARATOR));
}
