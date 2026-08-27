import type { Lane, LaneCaps, LaneFamily, LaneFamilyActiveCaps, LaneFamilyCaps } from './spec';

/**
 * A unit of work for the {@link Scheduler}. `run` resolves when the job is done and MUST NOT
 * reject (the orchestrator wraps execution so outcomes are values). `eligible` is re-checked
 * on every pump — it returns false while the job's dependencies/rules are unmet.
 */
export interface ScheduledJob {
  readonly id: string;
  readonly lane: Lane;
  /** Higher wins when contending for a free lane slot; ties fall back to FIFO. */
  readonly priority: number;
  readonly eligible: () => boolean;
  readonly run: () => Promise<void>;
}

export interface Scheduler {
  /** Enqueue a job; starts it immediately if a lane slot is free and it is eligible. */
  readonly submit: (job: ScheduledJob) => void;
  /** Re-evaluate the queue. Call whenever eligibility may have changed (a dep finished). */
  readonly pump: () => void;
  /** Remove a still-queued job (returns true if it was queued; running jobs are unaffected). */
  readonly drop: (id: string) => boolean;
  /**
   * Drop every queued job *and* release every running job's lane slot. Used by orchestrator reset.
   *
   * The slots must go too. A slot is freed from `run()`'s `finally`, and a reset abandons those
   * runs rather than resolving them, so anything live at reset would hold its lane for the life of
   * the process and the work submitted after it would queue forever.
   */
  readonly clear: () => void;
  readonly isRunning: (id: string) => boolean;
  readonly isQueued: (id: string) => boolean;
  readonly runningCount: (lane?: Lane) => number;
}

/**
 * A long-lived dynamic concurrency scheduler: work arrives over time, each lane has its own
 * cap, and a job only starts when a lane slot is free AND it is eligible. This is the proven
 * shape of `core/common/async/limited-parallelization-queue.ts`, generalized to lanes +
 * eligibility — it is intentionally NOT plainfp's `allWithConcurrency`, which only runs a
 * fixed batch.
 */
export function createScheduler(
  caps: LaneCaps = {},
  defaultCap = 4,
  families: LaneFamilyCaps = {},
  familyActive: LaneFamilyActiveCaps = {},
): Scheduler {
  const queue: ScheduledJob[] = [];
  /**
   * Keyed by the job itself, not by its id: two live jobs can legitimately share an id. Cancelling
   * a RUNNING activity settles it CANCELLED immediately while the scheduler still holds its job,
   * and `rerun` then accepts that terminal status and schedules a second job under the same id.
   * Keyed by id, the second `set` overwrote the first — `runningInLane` undercounted (the decode
   * lane ran 3 jobs at a cap of 2) and whichever job finished first deleted the *other* one's slot.
   */
  const running = new Map<ScheduledJob, Lane>();
  /**
   * Orders a family cap record longest prefix first, so a more specific family wins over a broader.
   *
   * @remarks
   * The record is partial, so unset entries are filtered out and what remains is narrowed by a
   * type guard rather than asserted.
   */
  const declared = (entries: LaneFamilyCaps): [LaneFamily, number][] =>
    Object.entries(entries)
      .filter((entry): entry is [LaneFamily, number] => entry[1] !== undefined)
      .sort(([a], [b]) => b.length - a.length);

  const familyPrefixes = declared(families);
  const activePrefixes = declared(familyActive);

  function capFor(lane: Lane): number {
    const exact = caps[lane];
    if (exact !== undefined)
      return exact;

    const family = familyPrefixes.find(([prefix]) => lane.startsWith(prefix));
    return family === undefined ? defaultCap : family[1];
  }

  /**
   * Would starting a job on `lane` exceed its family's active-lane cap? A lane that is already
   * running is free to take another job — the cap is on how many lanes are live, not on the work
   * inside them (that is {@link LaneFamilyCaps}).
   */
  function familyLaneBlocked(lane: Lane): boolean {
    const entry = activePrefixes.find(([prefix]) => lane.startsWith(prefix));
    if (entry === undefined)
      return false;

    const [prefix, maxActive] = entry;
    const active = new Set<Lane>();
    for (const jobLane of running.values()) {
      if (jobLane.startsWith(prefix))
        active.add(jobLane);
    }
    return !active.has(lane) && active.size >= maxActive;
  }

  function runningInLane(lane: Lane): number {
    let count = 0;
    for (const jobLane of running.values()) {
      if (jobLane === lane)
        count++;
    }
    return count;
  }

  function start(job: ScheduledJob): void {
    running.set(job, job.lane);
    // `run()` never rejects; the trailing catch only keeps the fire-and-forget chain from floating.
    job.run()
      .finally(() => {
        running.delete(job);
        pump();
      })
      .catch(() => {});
  }

  function pump(): void {
    for (;;) {
      let bestIndex = -1;
      let bestPriority = Number.NEGATIVE_INFINITY;
      for (const [index, job] of queue.entries()) {
        if (job.priority > bestPriority && runningInLane(job.lane) < capFor(job.lane) && !familyLaneBlocked(job.lane) && job.eligible()) {
          bestPriority = job.priority;
          bestIndex = index;
        }
      }
      if (bestIndex === -1)
        break;

      const [job] = queue.splice(bestIndex, 1);
      start(job);
    }
  }

  return {
    clear(): void {
      queue.length = 0;
      running.clear();
    },
    drop(id: string): boolean {
      const index = queue.findIndex(job => job.id === id);
      if (index === -1)
        return false;
      queue.splice(index, 1);
      return true;
    },
    isQueued: (id: string): boolean => queue.some(job => job.id === id),
    isRunning: (id: string): boolean => [...running.keys()].some(job => job.id === id),
    pump,
    runningCount: (lane?: Lane): number => (lane === undefined ? running.size : runningInLane(lane)),
    submit(job: ScheduledJob): void {
      queue.push(job);
      pump();
    },
  };
}
