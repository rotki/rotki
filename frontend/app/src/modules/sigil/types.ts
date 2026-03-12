/**
 * Sent once on login — app and user configuration data.
 */
export interface SessionConfigPayload {
  premium: boolean;
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
  exchangeCount: number;
  [key: `exchange_${string}`]: number;
}

/**
 * Sent once after balances finish loading — balance-dependent metrics.
 * Per-chain account counts are sent as dynamic `accounts_{chain}` keys.
 */
export interface BalancesSummaryPayload {
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
  id?: number;
  url: string;
  /** Set for custom events (chronicle calls), absent for page views. */
  name?: string;
  /** Custom event data payload. */
  data?: Record<string, unknown>;
  timestamp: number;
}

/** Payload shape for a single event sent to the analytics backend. */
export interface SigilEventPayload {
  website: string;
  hostname: string;
  screen: string;
  language: string;
  title: string;
  url: string;
  referrer: string;
  name?: string;
  data?: Record<string, unknown>;
}

export interface SigilBatchEntry {
  type: 'event';
  payload: SigilEventPayload;
}
