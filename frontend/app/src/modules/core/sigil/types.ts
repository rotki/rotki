/**
 * Sent once on login — app and user configuration data.
 */
export interface SessionConfigPayload {
  premium: boolean;
  /** Current subscription tier (e.g. "Free", "Basic", "Pro") */
  plan: string;
  appVersion: string;
  mainCurrency: string;
  language: string;
  theme: string;
  /** "electron" or "web" */
  appMode: string;
  /** Comma-separated list of price oracle identifiers */
  priceOracles: string;
}

/**
 * Sent once on login — connected exchange summary.
 * Per-exchange connection counts are sent as dynamic `exchange_{location}` keys.
 */
export interface ExchangesSummaryPayload {
  premium: boolean;
  plan: string;
  exchangeCount: number;
  [key: `exchange_${string}`]: number;
}

/**
 * Sent once after balances finish loading — balance-dependent metrics.
 * Per-chain account counts are sent as dynamic `accounts_{chain}` keys.
 */
export interface BalancesSummaryPayload {
  premium: boolean;
  plan: string;
  hasManualBalances: boolean;
  distinctAssetCount: number;
  totalAccounts: number;
  totalChains: number;
  [key: `accounts_${string}`]: number;
}

/**
 * Sent once after history sync completes — history event metrics.
 */
export interface HistorySyncPayload {
  premium: boolean;
  plan: string;
  /** Total number of history events across all sources */
  totalEvents: number;
  /** Number of events with ignored/spam assets */
  spamEvents: number;
  /** Number of event groups (transactions grouped by group identifier) */
  totalGroups: number;
}

export interface SigilEventMap {
  session_config: SessionConfigPayload;
  exchanges_summary: ExchangesSummaryPayload;
  balances_summary: BalancesSummaryPayload;
  history_sync: HistorySyncPayload;
}

export type SigilEvent = keyof SigilEventMap;

/** A queued entry stored in IndexedDB before being flushed via the batch endpoint. */
export interface SigilQueueEntry {
  /** IndexedDB key, not sent. */
  id?: number;
  /**
   * `identify` links the session to the client value; everything else is an event. Queued with the
   * rest rather than sent apart, so it keeps its place in the batch and survives being offline.
   */
  kind?: 'identify';
  url: string;
  /** Set for custom events (chronicle calls), absent for page views. */
  name?: string;
  /** Custom event data, or session data on an identify. */
  data?: Record<string, unknown>;
  /** The value to link the session to. Identify only. */
  clientId?: string;
  timestamp: number;
}

/** Payload shape for a single entry sent to the analytics backend. */
interface SigilEventPayload {
  website: string;
  hostname: string;
  screen: string;
  language: string;
  title: string;
  url: string;
  referrer: string;
  name?: string;
  data?: Record<string, unknown>;
  /** The distinct id, capped at 50 characters upstream. Identify only. */
  id?: string;
}

export interface SigilBatchEntry {
  type: 'event' | 'identify';
  payload: SigilEventPayload;
}
