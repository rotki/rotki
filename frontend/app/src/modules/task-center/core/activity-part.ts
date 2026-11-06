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
  SOLANA: 'solana',
  HYPERLIQUID: 'hyperliquid',
  BALANCES: 'balances',
  POOLS: 'pools',
  STATISTICS: 'statistics',
  STAKE: 'stake',
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
  EXCHANGE: 'exchange',
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
  /**
   * Scope facets: whether a flow covers everything or an explicit subset. A subset's members stay
   * raw values, appended after `CHAINS`.
   */
  ALL: 'all',
  CHAINS: 'chains',
  /**
   * A request naming the individual transactions and block events it covers, rather than a chain
   * or the whole set. The members stay raw values appended after this, as with `CHAINS`.
   */
  TARGETED: 'targeted',
} as const;

export type ActivityPart = (typeof ActivityPart)[keyof typeof ActivityPart];
