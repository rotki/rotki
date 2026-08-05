import type { BaseFetchOptions, EnqueueOptions, QueuedRequest, QueueOptions, QueueState, ResolvedEnqueueSettings } from './types';
import { FetchError } from 'ofetch';
import { reactive } from 'vue';
import { logger } from '@/modules/core/common/logging/logging';
import { QueueOverflowError, QueueTimeoutError, RequestCancelledError } from './errors';
import { createDedupeKey, generateId } from './request-identity';
import { RequestPriority } from './request-priority';
import { findEligibleIndex } from './slot-policy';

export type QueueFetchFn = <T>(url: string, options?: BaseFetchOptions) => Promise<T>;

export class RequestQueue {
  private queue: QueuedRequest[] = [];
  private readonly activeRequests = new Map<string, QueuedRequest>();
  private readonly pendingByKey = new Map<string, QueuedRequest>();
  private requestTimestamps: number[] = [];
  private readonly options: Required<QueueOptions>;
  private readonly fetchFn: QueueFetchFn;
  private isProcessing = false;
  private queueTimeoutCheckInterval: ReturnType<typeof setInterval> | null = null;
  private rateLimitRecoveryTimeout: ReturnType<typeof setTimeout> | null = null;
  readonly state: QueueState;

  constructor(fetchFn: QueueFetchFn, options?: QueueOptions) {
    this.fetchFn = fetchFn;
    this.options = {
      maxBackgroundConcurrent: 2,
      maxConcurrent: 6,
      maxPerSecond: 30,
      maxQueueSize: 100,
      maxQueueTime: 60000,
      maxRetries: 0,
      overflowStrategy: 'reject',
      overloadThreshold: 50,
      retryDelay: 1000,
      ...options,
    };
    this.state = reactive<QueueState>({
      active: 0,
      highPriorityQueued: 0,
      isOverloaded: false,
      queued: 0,
      requestsThisSecond: 0,
    });
    this.startQueueTimeoutCheck();
  }

  /** Resolved separately so the per-field defaults stay out of enqueue's own complexity budget. */
  private resolveEnqueueSettings(options: EnqueueOptions): ResolvedEnqueueSettings {
    const {
      dedupe = false,
      maxQueueTime = this.options.maxQueueTime,
      maxRetries = this.options.maxRetries,
      priority = RequestPriority.NORMAL,
      tags = [],
      ...fetchOptions
    } = options;

    return { dedupe, fetchOptions, maxQueueTime, maxRetries, priority, tags };
  }

  /** Attaches to an identical in-flight request, so both callers settle from the one response. */
  private subscribeToPending<T>(dedupeKey: string): Promise<T> | undefined {
    const existing = this.pendingByKey.get(dedupeKey);
    if (!existing)
      return undefined;

    return new Promise<T>((resolve, reject) => {
      existing.dedupeSubscribers ??= [];
      existing.dedupeSubscribers.push({ resolve, reject });
    });
  }

  private makeRoomIfFull(): void {
    if (this.queue.length < this.options.maxQueueSize)
      return;

    if (this.options.overflowStrategy === 'reject')
      throw new QueueOverflowError(`Queue is full (${this.options.maxQueueSize} requests)`);

    this.dropLowestPriority();
  }

  async enqueue<T>(url: string, options: EnqueueOptions = {}): Promise<T> {
    const { dedupe, fetchOptions, maxQueueTime, maxRetries, priority, tags } = this.resolveEnqueueSettings(options);
    const dedupeKey = dedupe ? createDedupeKey(url, fetchOptions) : null;

    if (dedupeKey) {
      const pending = this.subscribeToPending<T>(dedupeKey);
      if (pending)
        return pending;
    }

    this.makeRoomIfFull();

    const id = generateId();
    const abortController = new AbortController();

    return new Promise<T>((resolve, reject) => {
      const request: QueuedRequest<T> = {
        abortController,
        dedupeKey,
        id,
        maxQueueTime,
        maxRetries,
        options: { ...fetchOptions, signal: abortController.signal },
        priority,
        queuedAt: Date.now(),
        reject,
        resolve,
        retries: 0,
        tags,
        url,
      };
      if (dedupeKey)
        this.pendingByKey.set(dedupeKey, request);
      this.insertByPriority(request);
      this.updateState();
      this.processQueue().catch(error => logger.error(error));
    });
  }

  cancelByTag(tag: string): void {
    const error = new RequestCancelledError(`Cancelled by tag: ${tag}`);
    const toRemove: QueuedRequest[] = [];
    for (const request of this.queue) {
      if (request.tags.includes(tag)) {
        request.abortController.abort();
        this.rejectWithSubscribers(request, error);
        if (request.dedupeKey)
          this.pendingByKey.delete(request.dedupeKey);
        toRemove.push(request);
      }
    }
    this.queue = this.queue.filter(r => !toRemove.includes(r));

    for (const [id, request] of this.activeRequests) {
      if (request.tags.includes(tag)) {
        request.abortController.abort();
        this.rejectWithSubscribers(request, error);
        if (request.dedupeKey)
          this.pendingByKey.delete(request.dedupeKey);
        this.activeRequests.delete(id);
      }
    }
    this.updateState();
  }

  cancelById(id: string): void {
    const error = new RequestCancelledError(`Cancelled by id: ${id}`);
    const queueIndex = this.queue.findIndex(r => r.id === id);
    if (queueIndex !== -1) {
      const request = this.queue[queueIndex];
      request.abortController.abort();
      this.rejectWithSubscribers(request, error);
      if (request.dedupeKey)
        this.pendingByKey.delete(request.dedupeKey);
      this.queue.splice(queueIndex, 1);
      this.updateState();
      return;
    }
    const activeRequest = this.activeRequests.get(id);
    if (activeRequest) {
      activeRequest.abortController.abort();
      this.rejectWithSubscribers(activeRequest, error);
      if (activeRequest.dedupeKey)
        this.pendingByKey.delete(activeRequest.dedupeKey);
      this.activeRequests.delete(id);
      this.updateState();
    }
  }

  cancelAll(): void {
    const error = new RequestCancelledError('All requests cancelled');
    for (const request of this.queue) {
      request.abortController.abort();
      this.rejectWithSubscribers(request, error);
    }
    this.queue = [];
    for (const [, request] of this.activeRequests) {
      request.abortController.abort();
      this.rejectWithSubscribers(request, error);
    }
    this.activeRequests.clear();
    this.pendingByKey.clear();
    this.updateState();
  }

  getMetrics(): QueueState {
    return { ...this.state };
  }

  destroy(): void {
    if (this.queueTimeoutCheckInterval) {
      clearInterval(this.queueTimeoutCheckInterval);
      this.queueTimeoutCheckInterval = null;
    }
    if (this.rateLimitRecoveryTimeout) {
      clearTimeout(this.rateLimitRecoveryTimeout);
      this.rateLimitRecoveryTimeout = null;
    }
    for (const request of this.queue)
      request.abortController.abort();
    for (const [, request] of this.activeRequests)
      request.abortController.abort();
    this.queue = [];
    this.activeRequests.clear();
    this.pendingByKey.clear();
    this.updateState();
  }

  private insertByPriority(request: QueuedRequest): void {
    let insertIndex = this.queue.length;
    for (let i = 0; i < this.queue.length; i++) {
      if (this.queue[i].priority < request.priority) {
        insertIndex = i;
        break;
      }
    }
    this.queue.splice(insertIndex, 0, request);
  }

  private dropLowestPriority(): void {
    if (this.queue.length === 0)
      return;
    const lowest = this.queue.at(-1);
    if (lowest) {
      lowest.abortController.abort();
      this.rejectWithSubscribers(lowest, new QueueOverflowError('Dropped due to queue overflow'));
      if (lowest.dedupeKey)
        this.pendingByKey.delete(lowest.dedupeKey);
      this.queue.pop();
    }
  }

  private nextEligibleIndex(): number {
    return findEligibleIndex(this.queue, this.activeRequests.values(), this.options.maxBackgroundConcurrent);
  }

  private async processQueue(): Promise<void> {
    if (this.isProcessing)
      return;
    this.isProcessing = true;
    try {
      while (this.queue.length > 0) {
        if (this.activeRequests.size >= this.options.maxConcurrent) {
          break;
        }
        if (!this.canMakeRequest()) {
          this.scheduleRateLimitRecovery();
          break;
        }
        const index = this.nextEligibleIndex();
        if (index === -1)
          break;
        const [request] = this.queue.splice(index, 1);
        if (!request)
          break;
        this.activeRequests.set(request.id, request);
        this.recordRequestTimestamp();
        this.updateState();
        this.executeRequest(request).catch(error => logger.error(error));
      }
    }
    finally {
      this.isProcessing = false;
    }
  }

  private async executeRequest<T>(request: QueuedRequest<T>): Promise<void> {
    let shouldContinueProcessing = true;
    try {
      const response = await this.fetchFn<T>(request.url, request.options);
      this.cleanupRequest(request);
      this.resolveWithSubscribers(request, response);
    }
    catch (error) {
      if (this.shouldRetry(error, request)) {
        request.retries++;
        shouldContinueProcessing = false;
        const delay = this.options.retryDelay * (2 ** (request.retries - 1));
        setTimeout(() => {
          this.activeRequests.delete(request.id);
          this.insertByPriority(request);
          this.updateState();
          this.processQueue().catch(catchError => logger.error(catchError));
        }, delay);
        return;
      }
      this.cleanupRequest(request);
      this.rejectWithSubscribers(request, error);
    }
    finally {
      this.updateState();
      if (shouldContinueProcessing)
        this.processQueue().catch(error => logger.error(error));
    }
  }

  private resolveWithSubscribers<T>(request: QueuedRequest<T>, value: T): void {
    request.resolve(value);
    if (request.dedupeSubscribers) {
      for (const subscriber of request.dedupeSubscribers)
        subscriber.resolve(value);
    }
  }

  private rejectWithSubscribers<T>(request: QueuedRequest<T>, error: unknown): void {
    request.reject(error);
    if (request.dedupeSubscribers) {
      for (const subscriber of request.dedupeSubscribers)
        subscriber.reject(error);
    }
  }

  /** Rate limiting, unavailability and any server-side failure are all worth another attempt. */
  private isRetryableStatus(status: number | undefined): boolean {
    if (status === undefined)
      return false;

    return status === 429 || status === 503 || status >= 500;
  }

  private shouldRetry<T>(error: unknown, request: QueuedRequest<T>): boolean {
    if (request.retries >= request.maxRetries || request.abortController.signal.aborted)
      return false;
    if (error instanceof TypeError)
      return true;
    if (error instanceof DOMException && error.name === 'AbortError')
      return false;

    return error instanceof FetchError && this.isRetryableStatus(error.statusCode);
  }

  private cleanupRequest<T>(request: QueuedRequest<T>): void {
    this.activeRequests.delete(request.id);
    if (request.dedupeKey)
      this.pendingByKey.delete(request.dedupeKey);
  }

  private canMakeRequest(): boolean {
    const now = Date.now();
    this.requestTimestamps = this.requestTimestamps.filter(t => t > now - 1000);
    return this.requestTimestamps.length < this.options.maxPerSecond;
  }

  private recordRequestTimestamp(): void {
    this.requestTimestamps.push(Date.now());
  }

  private updateState(): void {
    const now = Date.now();
    this.requestTimestamps = this.requestTimestamps.filter(t => t > now - 1000);
    this.state.queued = this.queue.length;
    this.state.active = this.activeRequests.size;
    this.state.highPriorityQueued = this.queue.filter(r => r.priority >= RequestPriority.HIGH).length;
    this.state.isOverloaded = this.queue.length >= this.options.overloadThreshold;
    this.state.requestsThisSecond = this.requestTimestamps.length;
  }

  private startQueueTimeoutCheck(): void {
    this.queueTimeoutCheckInterval = setInterval(() => {
      const now = Date.now();
      const timedOut = this.queue.filter(r => now - r.queuedAt > r.maxQueueTime);
      for (const request of timedOut) {
        request.abortController.abort();
        this.rejectWithSubscribers(request, new QueueTimeoutError(`Request waited ${request.maxQueueTime}ms in queue`));
        if (request.dedupeKey)
          this.pendingByKey.delete(request.dedupeKey);
        const index = this.queue.indexOf(request);
        if (index !== -1)
          this.queue.splice(index, 1);
      }
      if (timedOut.length > 0)
        this.updateState();
    }, 5000);
  }

  private scheduleRateLimitRecovery(): void {
    if (this.rateLimitRecoveryTimeout || this.queue.length === 0)
      return;
    const now = Date.now();
    const oldestTimestamp = this.requestTimestamps.find(t => t > now - 1000);
    const delay = oldestTimestamp ? Math.max((oldestTimestamp + 1000) - now + 10, 10) : 50;
    this.rateLimitRecoveryTimeout = setTimeout(() => {
      this.rateLimitRecoveryTimeout = null;
      this.processQueue().catch(error => logger.error(error));
    }, delay);
  }
}
