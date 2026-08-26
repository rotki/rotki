import type { FetchOptions } from 'ofetch';

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

interface DedupeSubscriber {
  /**
   * `any` rather than `unknown`, deliberately: the queue holds requests whose result types are
   * unrelated, and `unknown` here makes every caller assert its request back into the element type.
   */
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
  /**
   * How many of {@link maxConcurrent} may be held at once by requests at or below
   * {@link RequestPriority.LOW} (default: 2). Priority alone cannot prevent starvation - it
   * orders the queue, and a queue cannot reorder slots that are already occupied - so this is
   * what keeps advisory background work from taking the whole budget and stopping the app.
   */
  maxBackgroundConcurrent?: number;
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
