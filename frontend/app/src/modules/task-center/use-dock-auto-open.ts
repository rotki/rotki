import type { Ref } from 'vue';
import type { Activity, ActivityId } from '@/modules/task-center/core/types';
import type { PendingJob } from '@/modules/task-center/use-pending-jobs';
import { useSetting } from '@/modules/settings/use-setting';

/** How long a clean run's summary stays open before the panel folds back into the pill. */
const SUMMARY_PEEK = 6000;

interface DockAutoOpenSources {
  /** Whether a batch is under way; it outlasts a short pause in the work. */
  readonly isActive: Readonly<Ref<boolean>>;
  /** Whether work is running right now, with no allowance for a pause. */
  readonly working: Readonly<Ref<boolean>>;
  readonly jobs: Readonly<Ref<PendingJob[]>>;
  /** Settled jobs with a failure, not yet dismissed; they may belong to an earlier batch. */
  readonly failed: Readonly<Ref<Activity[]>>;
  /** Settled jobs that finished cleanly, not yet dismissed. */
  readonly finished: Readonly<Ref<Activity[]>>;
  /** Jobs that failed before the dock mounted, reported with the batch running at mount. */
  readonly failedBeforeMount: readonly ActivityId[];
  /** Whether the pointer or focus is on the dock; a summary never folds away under it. */
  readonly interacting: Readonly<Ref<boolean>>;
  readonly modelExpanded: Ref<boolean>;
}

/**
 * When the dock opens its panel on its own.
 *
 * @remarks
 * It opens for two things only, and never on a timer while work runs:
 *
 * - A job the user started (`Activity.userStarted`), when it appears. Background work that starts on
 * its own only updates the pill. Once its batch settles, a panel opened this way is treated like a
 * summary: it folds away after a clean run, at once when the summary is off, and stays for a failure.
 * A panel the user opened themselves is theirs, so it is left as it is.
 * - The outcome of a batch, once everything settles, when the "show summary" setting is on. A clean
 * run folds back into the pill after {@link SUMMARY_PEEK}, held while the dock is hovered or
 * focused; a run with a failure stays open, since failures stay until they are dismissed. Only
 * the jobs of the batch that settled count: a failure left from an earlier batch does not open
 * the panel again.
 *
 * Collapsing the panel while work runs is taken as "leave me alone" for that batch: its summary is
 * skipped, and a job the user starts does not open the panel while that work is still running.
 * Once the work goes idle, a job the user starts is a new request and opens it again, even inside
 * the batch's grace period. The next batch starts fresh.
 */
export function useDockAutoOpen({ failed, failedBeforeMount, finished, interacting, isActive, jobs, modelExpanded, working }: DockAutoOpenSources): void {
  const showSummary = useSetting('dockShowSummary');
  const collapsedDuringBatch = shallowRef<boolean>(false);
  const collapsedWhileWorking = shallowRef<boolean>(false);
  const peeking = shallowRef<boolean>(false);
  /** Whether the panel is open because the dock opened it for a job the user started. */
  const openedForJob = shallowRef<boolean>(false);
  const seen = new Set<string>(get(isActive) ? failedBeforeMount : []);

  /**
   * Folds a summary back into the pill. `peeking` stays set until {@link rememberCollapse} sees the
   * panel close, so that close is not mistaken for the user collapsing it.
   */
  function endPeek(): void {
    if (get(peeking))
      set(modelExpanded, false);
  }

  const { start: startPeek, stop: stopPeek } = useTimeoutFn(endPeek, SUMMARY_PEEK, { immediate: false });

  /** Opens the panel for a job the user started, the first time the dock sees it running. */
  function openForUserStartedJobs(list: PendingJob[]): void {
    const started = list.filter(job => !seen.has(job.activity.id));
    for (const job of started)
      seen.add(job.activity.id);

    if (get(collapsedWhileWorking) || !started.some(job => job.activity.userStarted))
      return;

    if (!get(modelExpanded) || get(peeking))
      set(openedForJob, true);
    stopPeek();
    set(peeking, false);
    set(modelExpanded, true);
  }

  /** A collapse while work runs holds off every automatic open until the batch settles. */
  function rememberCollapse(open: boolean, wasOpen: boolean | undefined): void {
    if (open || !wasOpen)
      return;
    set(openedForJob, false);
    if (get(peeking)) {
      set(peeking, false);
      return;
    }
    if (get(isActive))
      set(collapsedDuringBatch, true);
    if (get(working))
      set(collapsedWhileWorking, true);
  }

  /** Once the work goes idle, the user's next job is a new request, so the collapse no longer holds it shut. */
  function releaseCollapse(running: boolean): void {
    if (!running)
      set(collapsedWhileWorking, false);
  }

  function inBatch(roots: Activity[]): boolean {
    return roots.some(root => seen.has(root.id));
  }

  function peek(): void {
    set(peeking, true);
    set(modelExpanded, true);
    startPeek();
  }

  /**
   * When a batch settles, shows its outcome unless the user collapsed the panel during it. A panel
   * the dock opened for a job the user started gets the same treatment as a summary; one the user
   * opened themselves is left as it is.
   */
  function summarize(active: boolean, wasActive: boolean | undefined): void {
    if (active) {
      if (get(peeking)) {
        stopPeek();
        endPeek();
      }
      return;
    }
    if (!wasActive)
      return;

    const collapsed = get(collapsedDuringBatch);
    const ours = get(openedForJob);
    const batchFailed = inBatch(get(failed));
    const batchFinished = inBatch(get(finished));
    set(collapsedDuringBatch, false);
    set(openedForJob, false);
    seen.clear();
    if (collapsed)
      return;
    if (ours)
      settleOpenedForJob(batchFailed, batchFinished);
    else
      showOutcome(batchFailed, batchFinished);
  }

  /** A panel opened for the user's job stays for a failure, and otherwise folds away like a summary. */
  function settleOpenedForJob(batchFailed: boolean, batchFinished: boolean): void {
    if (batchFailed)
      return;
    if (batchFinished && get(showSummary))
      peek();
    else
      set(modelExpanded, false);
  }

  /** Opens the panel on the batch's outcome, unless the summary is off or the user has it open already. */
  function showOutcome(batchFailed: boolean, batchFinished: boolean): void {
    if (!get(showSummary) || get(modelExpanded))
      return;
    if (batchFailed)
      set(modelExpanded, true);
    else if (batchFinished)
      peek();
  }

  /** Holds a summary open while the dock is touched, and gives it the full time again once it is left. */
  function holdPeek(touched: boolean): void {
    if (!get(peeking))
      return;
    if (touched)
      stopPeek();
    else
      startPeek();
  }

  watch(jobs, openForUserStartedJobs, { immediate: true });
  watch(modelExpanded, rememberCollapse);
  watch(working, releaseCollapse);
  watch(isActive, summarize);
  watch(interacting, holdPeek);
}
