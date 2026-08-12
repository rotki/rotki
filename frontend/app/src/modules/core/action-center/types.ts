import type { RuiIcons } from '@rotki/ui-library';
import type { RouteLocationRaw } from 'vue-router';
import type { Pinned } from '@/modules/session/types';

/**
 * How much attention a row asks for. `WARNING` needs a decision from the user,
 * `INFO` is a to-do that resolves on its own once data is processed and `MUTED`
 * is handled automatically (rotki retries) and is only worth a look.
 */
export const ActionSeverity = {
  INFO: 'info',
  MUTED: 'muted',
  WARNING: 'warning',
} as const;

export type ActionSeverity = (typeof ActionSeverity)[keyof typeof ActionSeverity];

/**
 * The targets every action center understands.
 *
 * A domain that needs more than these (its own dialog, a scoped view of its own
 * table) extends this union with its own kinds and resolves them in the component
 * that hosts the center - the generic components only ever hand a target back up.
 */
export type ActionTarget =
  | { kind: 'route'; to: RouteLocationRaw }
  /** Opens a panel in the pinned rail. */
  | { kind: 'pin'; panel: Pinned }
  | { kind: 'run'; run: () => void };

/**
 * One row of an action center: something the user could do, with a count of how
 * much of it there is and one way to get there.
 */
export interface ActionItem<TTarget extends { kind: string } = ActionTarget, TId extends string = string> {
  /** Rendered into `data-testid`, so the values are kebab-case like every other test id. */
  id: TId;
  icon: RuiIcons;
  title: string;
  description: string;
  actionLabel: string;
  count: number;
  severity: ActionSeverity;
  /** while true the count is not trustworthy yet, so the row is not counted as active */
  loading: boolean;
  /** the count is visible but every action behind it needs premium the user lacks */
  locked: boolean;
  /** tier that would unlock the row, when known */
  minimumTier: string | null;
  /** nothing is pending anymore, the count is what the user chose to set aside */
  informational: boolean;
  /** where the row's action leads */
  target: TTarget;
  /** where the category is opened from the cleared strip, when it has nothing pending */
  checkTarget: TTarget;
}

/** The parts of a row that are the same for every item unless stated otherwise. */
export type ActionItemDefinition<TTarget extends { kind: string }, TId extends string = string> =
  Omit<ActionItem<TTarget, TId>, 'loading' | 'locked' | 'minimumTier' | 'informational' | 'checkTarget'>
  & Partial<Pick<ActionItem<TTarget, TId>, 'loading' | 'locked' | 'minimumTier' | 'informational' | 'checkTarget'>>;

export function createActionItem<TTarget extends { kind: string }, TId extends string>(
  definition: ActionItemDefinition<TTarget, TId>,
): ActionItem<TTarget, TId> {
  return {
    checkTarget: definition.target,
    informational: false,
    loading: false,
    locked: false,
    minimumTier: null,
    ...definition,
  };
}
