type Fn = () => Promise<void>;

type OnCompletion = (() => void) | undefined;

/**
 * An execution queue where you can queue tasks for work and
 * ensure that only a specific number of them will run in parallel.
 */
export class LimitedParallelizationQueue {
  private runningTasks: Map<string, Fn> = new Map();
  private pendingTasks: Map<string, Fn> = new Map();
  private onCompletion: OnCompletion = undefined;

  /**
   * Creates a new SemiParallelExecutionQueue. If not specified
   * the parallelization is set to 5 tasks.
   *
   * @param parallelization the number of tasks to run in parallel
   */
  constructor(private parallelization: number = 5) {}

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
    await fn();
    this.runningTasks.delete(identifier);

    if (this.pending > 0) {
      const entries = this.pendingTasks.entries();
      const next = entries.next();
      if (!next.done) {
        const [identifier, promise] = next.value;
        this.pendingTasks.delete(identifier);
        startPromise(this.run(identifier, promise));
      }
    } else if (this.running === 0) {
      this.onCompletion?.();
    }
  }

  setOnCompletion(onCompletion: OnCompletion) {
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
      if (this.runningTasks.has(identifier)) {
        this.pendingTasks.set(identifier, fn);
      } else {
        startPromise(this.run(identifier, fn));
      }
    } else {
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
