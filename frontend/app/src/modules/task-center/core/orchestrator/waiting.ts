import type { ActivitySpec } from './spec';
import { isTerminalStatus } from '../status';
import { type Activity, type ActivityId, type ActivityStatus, type ActivityWaiting, ActivityStatus as Status, WaitingReason } from '../types';
import { type EligibilityRule, firstRuleHold } from './rules';

/** The part of an orchestrator record the hold checks read; the orchestrator's records satisfy it structurally. */
export interface HeldRecord {
  readonly spec: Pick<ActivitySpec, 'deps' | 'parent'>;
  readonly status: ActivityStatus;
}

/** What the hold checks read besides the record itself. */
export interface HoldContext {
  readonly records: ReadonlyMap<ActivityId, HeldRecord>;
  readonly rules: readonly EligibilityRule[];
  /** Every activity, projected; what the rules judge the candidate against. */
  readonly all: readonly Activity[];
}

function unsettledDependency(record: HeldRecord, records: ReadonlyMap<ActivityId, HeldRecord>): ActivityId | undefined {
  return (record.spec.deps ?? []).find((id) => {
    const dep = records.get(id);
    return dep !== undefined && !isTerminalStatus(dep.status);
  });
}

/**
 * What holds a pending record back before any lane is considered, or `undefined` when nothing does.
 *
 * @remarks
 * The checks run in the order the scheduler gates a job, so the first one found is also why the
 * job has not started: a parent that has not started, then a dependency that has not settled, then
 * the rules in their configured order. A missing parent or dependency does not hold anything, as it
 * never will settle.
 *
 * @param record - The pending record.
 * @param candidate - The same record, projected, for the rules to judge.
 * @param context - The other records and activities the checks read.
 * @returns The hold, naming what it waits on where there is one.
 */
export function holdOf(record: HeldRecord, candidate: Activity, context: HoldContext): ActivityWaiting | undefined {
  const parent = record.spec.parent;
  if (parent !== undefined && context.records.get(parent)?.status === Status.PENDING)
    return { on: parent, reason: WaitingReason.PARENT };

  const dependency = unsettledDependency(record, context.records);
  if (dependency !== undefined)
    return { on: dependency, reason: WaitingReason.DEPENDENCY };

  return firstRuleHold(context.rules, candidate, context.all);
}
