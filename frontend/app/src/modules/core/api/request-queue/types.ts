import type { FetchOptions } from 'ofetch';

/** FetchOptions without the 'priority' field to avoid conflict with our queue priority */
/**
 * Options the queue carries but never reads: they are handed back to the fetch function untouched.
 * `retry` is excluded from ofetch's shape because the caller's own retry contract travels under that
 * name, and the queue is in no position to say which one it is.
 */
export type BaseFetchOptions = Omit<FetchOptions<'json'>, 'priority' | 'retry'> & {
  retry?: unknown;
};

export interface QueueState {
  /** Number of requests waiting in queue */
  queued: number;
  /** Number of requests currently in-flight */
  active: number;
  /** Number of high-priority requests waiting */
  highPriorityQueued: number;
  /** True when queue is larger than threshold */
  isOverloaded: boolean;
  /** Requests processed in the last second */
  requestsThisSecond: number;
}

export interface DedupeSubscriber {
  // The queue holds requests whose result types are unrelated, which TypeScript cannot express.
  // `any` in the parameter position is what makes a QueuedRequest<T> storable next to the others;
  // with `unknown` every caller has to assert the request back into the queue's element type.
  resolve: (value: any) => void;
  reject: (error: unknown) => void;
}

export interface QueuedRequest<T = any> {
  id: string;
  url: string;
  options: BaseFetchOptions;
  priority: number;
  tags: string[];
  queuedAt: number;
  maxQueueTime: number;
  retries: number;
  maxRetries: number;
  abortController: AbortController;
  resolve: (value: T) => void;
  reject: (error: unknown) => void;
  /** Key used for deduplication, null if not deduped */
  dedupeKey: string | null;
  /** Additional subscribers waiting for the same deduplicated request */
  dedupeSubscribers?: DedupeSubscriber[];
}

export interface QueueOptions {
  /** Maximum concurrent requests (default: 6, browser optimal) */
  maxConcurrent?: number;
  /** Maximum requests per second (default: 30) */
  maxPerSecond?: number;
  /** Base retry delay in ms (default: 1000) */
  retryDelay?: number;
  /** Maximum retry attempts (default: 0, no retry) */
  maxRetries?: number;
  /** Maximum queue size before overflow (default: 100) */
  maxQueueSize?: number;
  /** Maximum time in queue before timeout in ms (default: 60000) */
  maxQueueTime?: number;
  /** Strategy when queue is full */
  overflowStrategy?: 'reject' | 'dropLowest';
  /** Threshold for isOverloaded flag (default: 50) */
  overloadThreshold?: number;
}

export interface EnqueueOptions extends BaseFetchOptions {
  /** Request priority (higher = processed first) */
  priority?: number;
  /** Tags for group cancellation */
  tags?: string[];
  /** Override max retries */
  maxRetries?: number;
  /** Override max queue time */
  maxQueueTime?: number;
  /** Deduplicate identical pending requests */
  dedupe?: boolean;
}

/** The enqueue options with every default applied, split from the options passed on to fetch. */
export interface ResolvedEnqueueSettings {
  dedupe: boolean;
  fetchOptions: BaseFetchOptions;
  maxQueueTime: number;
  maxRetries: number;
  priority: number;
  tags: string[];
}
