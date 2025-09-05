import type { BalanceQueryProgressType } from '@/modules/dashboard/progress/types';
import { startPromise } from '@shared/utils';

export interface QueueItemMetadata {
  chain: string;
  address?: string;
  [key: string]: any;
}

export interface QueueItem<T extends QueueItemMetadata = QueueItemMetadata> {
  id: string;
  type: BalanceQueryProgressType;
  executeFn: () => Promise<void>;
  metadata: T;
  status?: 'pending' | 'running' | 'completed' | 'failed';
  addedAt?: number;
}

export interface QueueStats {
  pending: number;
  running: number;
  completed: number;
  failed: number;
  total: number;
}

interface BatchInfo {
  resolve: () => void;
  reject: (error: Error) => void;
  totalItems: number;
  completedItems: number;
  failedItems: number;
}

export class BalanceQueueService<T extends QueueItemMetadata = QueueItemMetadata> {
  private static instance: BalanceQueueService<any>;

  private queue: QueueItem<T>[] = [];
  private runningItems = new Map<string, QueueItem<T>>();
  private completedItems = new Map<string, QueueItem<T>>();
  private failedItems = new Map<string, QueueItem<T>>();

  private maxConcurrency: number;

  private batches = new Map<string, Set<string>>();
  private batchPromises = new Map<string, BatchInfo>();
  private itemPromises = new Map<string, { resolve: () => void; reject: (error: Error) => void }>();

  private onCompletionCallback?: () => void;
  private onProgressCallback?: (stats: QueueStats) => void;

  constructor(maxConcurrency = 2) {
    this.maxConcurrency = maxConcurrency;
  }

  static getInstance<T extends QueueItemMetadata = QueueItemMetadata>(maxConcurrency = 2): BalanceQueueService<T> {
    if (!this.instance) {
      this.instance = new BalanceQueueService<T>(maxConcurrency);
    }
    return this.instance as BalanceQueueService<T>;
  }

  static resetInstance(): void {
    if (this.instance) {
      this.instance.clear();
      this.instance = undefined as any;
    }
  }

  setOnCompletion(callback: (() => void) | undefined): void {
    this.onCompletionCallback = callback;
  }

  setOnProgress(callback: ((stats: QueueStats) => void) | undefined): void {
    this.onProgressCallback = callback;
  }

  async enqueue(item: QueueItem<T>): Promise<void> {
    const queueItem: QueueItem<T> = {
      ...item,
      addedAt: Date.now(),
      status: 'pending',
    };

    this.queue.push(queueItem);

    // Create a promise that resolves when this specific item completes
    const promise = new Promise<void>((resolve, reject) => {
      this.itemPromises.set(item.id, { reject, resolve });
    });

    startPromise(this.processNext());

    return promise;
  }

  async enqueueBatch(items: QueueItem<T>[]): Promise<void> {
    if (items.length === 0)
      return;

    const batchId = `batch-${Date.now()}-${Math.random()}`;
    const itemIds = new Set<string>();

    for (const item of items) {
      const queueItem: QueueItem<T> = {
        ...item,
        addedAt: Date.now(),
        status: 'pending',
      };

      itemIds.add(item.id);
      this.queue.push(queueItem);
    }

    this.batches.set(batchId, itemIds);

    const promise = new Promise<void>((resolve, reject) => {
      this.batchPromises.set(batchId, {
        completedItems: 0,
        failedItems: 0,
        reject,
        resolve,
        totalItems: items.length,
      });
    });

    startPromise(this.processNext());

    return promise;
  }

  private async processNext(): Promise<void> {
    while (this.runningItems.size < this.maxConcurrency && this.queue.length > 0) {
      const item = this.queue.shift();
      if (!item)
        break;

      item.status = 'running';
      this.runningItems.set(item.id, item);

      this.notifyProgress();

      startPromise(this.executeItem(item));
    }
  }

  private async executeItem(item: QueueItem<T>): Promise<void> {
    try {
      await item.executeFn();

      item.status = 'completed';
      this.runningItems.delete(item.id);
      this.completedItems.set(item.id, item);

      this.onItemComplete(item.id, true);
    }
    catch (error) {
      item.status = 'failed';
      this.runningItems.delete(item.id);
      this.failedItems.set(item.id, item);

      console.error(`Queue item ${item.id} failed:`, error);
      this.onItemComplete(item.id, false);
    }
    finally {
      this.notifyProgress();
      await this.processNext();

      if (this.runningItems.size === 0 && this.queue.length === 0) {
        this.onCompletionCallback?.();
      }
    }
  }

  private onItemComplete(itemId: string, success: boolean): void {
    // Resolve individual item promise
    const itemPromise = this.itemPromises.get(itemId);
    if (itemPromise) {
      itemPromise.resolve();
      this.itemPromises.delete(itemId);
    }

    // Check batch promises
    for (const [batchId, items] of this.batches) {
      if (items.has(itemId)) {
        items.delete(itemId);

        const batch = this.batchPromises.get(batchId);
        if (batch) {
          if (success)
            batch.completedItems++;
          else
            batch.failedItems++;

          if (batch.completedItems + batch.failedItems >= batch.totalItems) {
            batch.resolve();
            this.batchPromises.delete(batchId);
            this.batches.delete(batchId);
          }
        }
      }
    }
  }

  private notifyProgress(): void {
    if (this.onProgressCallback) {
      this.onProgressCallback(this.getStats());
    }
  }

  clear(): void {
    this.queue = [];
    this.runningItems.clear();

    // Reject all pending item promises
    for (const [, promise] of this.itemPromises) {
      promise.reject(new Error('Queue cleared'));
    }
    this.itemPromises.clear();

    // Reject all pending batch promises
    for (const [, promise] of this.batchPromises) {
      promise.reject(new Error('Queue cleared'));
    }

    this.batches.clear();
    this.batchPromises.clear();
  }

  clearCompleted(): void {
    this.completedItems.clear();
    this.failedItems.clear();
  }

  getStats(): QueueStats {
    return {
      completed: this.completedItems.size,
      failed: this.failedItems.size,
      pending: this.queue.length,
      running: this.runningItems.size,
      total: this.queue.length + this.runningItems.size + this.completedItems.size + this.failedItems.size,
    };
  }

  getItems(): {
    pending: QueueItem<T>[];
    running: QueueItem<T>[];
    completed: QueueItem<T>[];
    failed: QueueItem<T>[];
  } {
    return {
      completed: Array.from(this.completedItems.values()),
      failed: Array.from(this.failedItems.values()),
      pending: [...this.queue],
      running: Array.from(this.runningItems.values()),
    };
  }

  getAllItems(): QueueItem<T>[] {
    return [
      ...this.queue,
      ...Array.from(this.runningItems.values()),
      ...Array.from(this.completedItems.values()),
      ...Array.from(this.failedItems.values()),
    ];
  }

  getProgress(): number {
    const stats = this.getStats();
    if (stats.total === 0)
      return 0;

    return Math.round(((stats.completed + stats.failed) / stats.total) * 100);
  }

  isProcessing(): boolean {
    return this.runningItems.size > 0 || this.queue.length > 0;
  }
}
