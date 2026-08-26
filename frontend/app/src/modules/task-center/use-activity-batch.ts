import type { TaskError } from '@/modules/core/tasks/task-result';
import type { ActivityId, ActivityKind, ActivityText } from '@/modules/task-center/core/types';
import { ok, type Result } from 'plainfp/result';
import { UMBRELLA_LANE } from '@/modules/task-center/core/orchestrator/spec';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface BatchLabels {
  readonly title: string;
  readonly subtitle?: ActivityText;
}

/**
 * The umbrella row a fan-out runs under. The id is built by the caller from its descriptor
 * (`descriptor.batchId([chain])`), where the key type is concrete and the prefix is still checked;
 * taking the descriptor and the prefix here instead would put `Prefixes<TKey>` in an inference
 * position it cannot be recovered from, and every call would collapse to the empty prefix.
 */
interface BatchUmbrella extends BatchLabels {
  readonly id: ActivityId;
  readonly kind: ActivityKind;
  /**
   * The umbrella's own parent, when this batch is itself part of a larger one — a CSV import fans
   * out over rows, each of which fans out over addresses. Passed through to the children when the
   * umbrella is suppressed, so a single-item batch does not orphan its child from the outer batch.
   */
  readonly parent?: ActivityId;
  /**
   * Keep this umbrella out of the completion ledger — see {@link ActivitySpec.container}.
   *
   * Opt-in per caller, because it is not always right: an umbrella that *is* the subject for its
   * kind (`HISTORY_SYNC`) has a load-bearing ledger entry. Set it where the children are the
   * subjects and the umbrella is only their container.
   */
  readonly container?: boolean;
}

interface UseActivityBatchReturn {
  runActivityBatch: <TItem, TResult>(
    umbrella: BatchUmbrella,
    items: readonly TItem[],
    run: (item: TItem, parent: ActivityId | undefined) => Promise<TResult>,
  ) => Promise<TResult[]>;
}

export function useActivityBatch(): UseActivityBatchReturn {
  const { submitTask } = useNativeTask();

  /**
   * Runs one activity per subject under a single umbrella row.
   *
   * Throttling is the lane's job: each subject's own submit carries the descriptor's lane, so adding
   * a limiter here would put two mechanisms on one piece of work.
   *
   * The umbrella runs on {@link UMBRELLA_LANE}, never the children's lane: a parent holding a slot
   * in the lane it is waiting on throttles its own children, and at a cap of 1 deadlocks.
   */
  async function runActivityBatch<TItem, TResult>(
    umbrella: BatchUmbrella,
    items: readonly TItem[],
    run: (item: TItem, parent: ActivityId | undefined) => Promise<TResult>,
  ): Promise<TResult[]> {
    if (items.length === 0)
      return [];

    if (items.length === 1)
      return [await run(items[0], umbrella.parent)];

    const batchId = umbrella.id;

    // The umbrella is submitted before its children so the parent gate applies to them, but its
    // `run` needs their promises, which only exist once submitted.
    let declared!: (work: readonly Promise<TResult>[]) => void;
    const subtree = new Promise<readonly Promise<TResult>[]>((resolve) => {
      declared = resolve;
    });

    const batch = submitTask({
      id: batchId,
      container: umbrella.container,
      kind: umbrella.kind,
      lane: UMBRELLA_LANE,
      parent: umbrella.parent,
      rerunnable: false,
      run: async (): Promise<Result<void, TaskError>> => {
        await Promise.allSettled(await subtree);
        return ok(undefined);
      },
      subtitle: umbrella.subtitle,
      title: umbrella.title,
    });

    const work = items.map(async item => run(item, batchId));
    declared(work);

    // Results come from the children, not through the umbrella: a second batch over the same prefix
    // dedups onto the first umbrella, and reading its outcome would report the wrong run's work.
    const results = await Promise.all(work);
    await batch;
    return results;
  }

  return { runActivityBatch };
}
