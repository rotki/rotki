import { startPromise } from '@shared/utils';
import { logger } from '@/modules/core/common/logging/logging';

type Fn = () => Promise<void>;

type OnCompletion = (() => void) | undefined;

/**
 * An execution queue where you can queue tasks for work and
 * ensure that only a specific number of them will run in parallel.
 */
export class LimitedParallelizationQueue {
  private readonly runningTasks: Map<string, Fn> = new Map();
  private readonly pendingTasks: Map<string, Fn> = new Map();
  private onCompletion: OnCompletion = undefined;

  /**
   * Creates a new SemiParallelExecutionQueue. If not specified
   * the parallelization is set to 5 tasks.
   *
   * @param parallelization the number of tasks to run in parallel
   */
  constructor(private readonly parallelization: number = 5) {}

  /**
   * The number of pending tasks
   */
  get pending(): number {
    return this.pendingTasks.size;
  }

  /**
   * The number of running tasks
   */
  get running(): number {
    return this.runningTasks.size;
  }

  private async run(identifier: string, fn: Fn): Promise<void> {
    this.runningTasks.set(identifier, fn);
    try {
      await fn();
    }
    catch (error: unknown) {
      // A rejected task must not strand its slot. Without this the bookkeeping below was skipped
      // entirely: the identifier stayed in `runningTasks`, no queued task was ever started, and
      // `onCompletion` never fired — so `awaitParallelExecution` waited forever rather than
      // failing. The queue's contract is fire-and-forget, so the error is logged, not rethrown.
      logger.error(error);
    }

    this.runningTasks.delete(identifier);
    this.pump();
  }

  /** Start the next pending task, or announce completion when nothing is left. */
  private pump(): void {
    if (this.pending > 0) {
      const entries = this.pendingTasks.entries();
      const next = entries.next();
      if (!next.done) {
        const [identifier, promise] = next.value;
        this.pendingTasks.delete(identifier);
        startPromise(this.run(identifier, promise));
      }
    }
    else if (this.running === 0) {
      this.onCompletion?.();
    }
  }

  setOnCompletion(onCompletion: OnCompletion): void {
    this.onCompletion = onCompletion;
  }

  /**
   * Queues a Promise<void> returning function for execution
   *
   * @param identifier used to identify the task
   * @param fn a function that returns a Promise<void>
   */
  queue(identifier: string, fn: Fn): void {
    if (this.runningTasks.size < this.parallelization) {
      if (this.runningTasks.has(identifier))
        this.pendingTasks.set(identifier, fn);
      else
        startPromise(this.run(identifier, fn));
    }
    else {
      this.pendingTasks.set(identifier, fn);
    }
  }

  /**
   * Clears any pending tasks from the execution queue
   */
  clear(): void {
    this.pendingTasks.clear();
  }
}
