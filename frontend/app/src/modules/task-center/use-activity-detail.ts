import type { ComputedRef } from 'vue';
import type { ActivityDescriptor } from '@/modules/task-center/core/activity-descriptor';
import type { ActivityId } from '@/modules/task-center/core/types';

/**
 * The side channel carrying per-activity detail, beside the ledger rather than inside it.
 *
 * Every entry is keyed by the same {@link ActivityId} the orchestrator uses, so detail and record
 * are joined by identity and nothing has to thread a second key through the spine. The channel
 * holds `unknown`; the only way in and out is through a descriptor, which is what makes the shape
 * checked at both ends.
 *
 * @remarks
 * A plain singleton rather than a Pinia store, because its lifetime belongs to the orchestrator: the
 * spine drops an entry when the record it describes is replaced, re-run or pruned, and the spine is
 * framework-agnostic. As a store that edge cost more than it bought — Pinia re-activates the
 * instance an action was bound to before running it, so the orchestrator could not hold the actions
 * it needs without pinning the whole process to whichever Pinia was active when it was first
 * constructed. Logout is covered by `orchestrator.reset()`, which is stricter than the global store
 * reset anyway: it also fires on re-run, re-submit and prune.
 */
export const useActivityDetail = createGlobalState(() => {
  const details = shallowRef<Record<ActivityId, unknown>>({});

  function setDetail(id: ActivityId, detail: unknown): void {
    set(details, { ...get(details), [id]: detail });
  }

  function dropDetail(id: ActivityId): void {
    const current = get(details);
    if (!(id in current))
      return;

    const next = { ...current };
    delete next[id];
    set(details, next);
  }

  function resetDetails(): void {
    set(details, {});
  }

  return {
    details,
    dropDetail,
    resetDetails,
    setDetail,
  };
});

/**
 * Publish one subject's detail.
 *
 * Uncallable for an activity that declares no detail: its `TDetail` is `never`, and no value
 * inhabits `never`, so there is no third argument to pass. That is the compile-time half of "detail
 * is opt in per kind".
 *
 * `NoInfer` is what makes that hold. Without it the detail argument is an inference site of equal
 * weight to the descriptor, so passing a detail to a `never` activity simply widens `TDetail` to
 * whatever was passed and the call compiles.
 */
export function publishActivityDetail<TSubject, TKey extends readonly (string | number)[], TDetail>(
  descriptor: ActivityDescriptor<TSubject, TKey, TDetail>,
  subject: TSubject,
  detail: NoInfer<TDetail>,
): void {
  useActivityDetail().setDetail(descriptor.id(subject), detail);
}

/**
 * Read one subject's detail, typed by the descriptor that published it.
 *
 * Reading kind A's detail through kind B's descriptor does not type-check, because the subject and
 * the returned shape both come from the descriptor passed in. `undefined` is a normal answer: an
 * activity is submitted before anything has been streamed about it, and detail is dropped when the
 * activity is cleared.
 *
 * The channel holds `unknown` by design, so this is the single narrowing point for the whole
 * channel. What makes it sound is that the id was minted by the same descriptor: nothing else can
 * write that key, so nothing else can put another shape behind it.
 */
export function readActivityDetail<TSubject, TKey extends readonly (string | number)[], TDetail>(
  descriptor: ActivityDescriptor<TSubject, TKey, TDetail>,
  subject: TSubject,
): ComputedRef<TDetail | undefined> {
  const { details } = useActivityDetail();
  const id = descriptor.id(subject);

  // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- the channel holds `unknown` by design; the descriptor pairs the writer and this reader
  return computed<TDetail | undefined>(() => get(details)[id] as TDetail | undefined);
}
