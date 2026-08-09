import type { ActivityContext, RunBackendTask } from '@/modules/task-center/use-native-task';

/**
 * The shape a producer spec has from a stubbed `submitTask`'s point of view: enough to run it,
 * and the two id fields specs assert on.
 */
export interface SubmittedSpec {
  id: string;
  kind: string;
  run: (ctx: ActivityContext) => Promise<unknown>;
  /** Declared so a spec can assert scheduling intent (an umbrella's lane, a child's parent). */
  lane?: string;
  parent?: string;
}

/**
 * Builds a `submitTask` stub that runs the submitted spec inline, the way `useNativeTask` does:
 * with a no-op progress sink and the task runner the spec is given.
 *
 * The runner is passed in rather than pulled off a mocked module, mirroring production — there
 * the orchestrator hands each activity a runner bound to it. Use `vi.fn(runSpecWith(runTask))`
 * and keep asserting on `runTask` as before.
 */
export function runSpecWith(runTask: RunBackendTask): (spec: SubmittedSpec) => Promise<unknown> {
  return async (spec: SubmittedSpec): Promise<unknown> => spec.run({ cancelled: () => false, report: () => {}, runTask });
}
