import type { RuiIcons } from '@rotki/ui-library';
import type { RouteLocationRaw } from 'vue-router';
import type { Pinned } from '@/modules/session/types';
import type { SettingsCategoryId, SettingsHighlightId } from '@/modules/settings/setting-highlight-ids';
import { flatMap } from 'plainfp/arrays';
import { match, type Option } from 'plainfp/option';

/**
 * What a row asks of the user, which sets how loudly it is drawn.
 *
 * @remarks
 * An actionability axis rather than a severity, so it stays apart from the notifications' `Severity`.
 * `DECISION` needs the user to decide something, `TODO` is work that resolves once data is
 * processed, and `AUTOMATIC` is handled by rotki (it retries) and is only worth a look.
 */
export const ActionUrgency = {
  AUTOMATIC: 'automatic',
  DECISION: 'decision',
  TODO: 'todo',
} as const;

export type ActionUrgency = (typeof ActionUrgency)[keyof typeof ActionUrgency];

/**
 * The targets every action center understands.
 *
 * A domain that needs more than these (its own dialog, a scoped view of its own
 * table) extends this union with its own kinds and resolves them in the component
 * that hosts the center - the generic components only ever hand a target back up.
 */
export type ActionTarget =
  /**
   * `highlight` names the settings entry to scroll to and flash once the page is up. A settings page
   * scrolls its own container, so a `#hash` in the route would not reach the entry.
   */
  | { kind: 'route'; to: RouteLocationRaw; highlight?: SettingsCategoryId | SettingsHighlightId }
  /** Opens a panel in the pinned rail. */
  | { kind: 'pin'; panel: Pinned }
  /** Opens a page outside the app, in the system browser on the desktop app. */
  | { kind: 'external'; url: string }
  /**
   * Acts in place, so the center stays open to show the outcome, unless `closesCenter` says the run
   * opens a surface of its own, such as a dialog.
   */
  | { kind: 'run'; run: () => void; closesCenter?: boolean };

/** Something a row offers besides its main action, listed in the row's menu. */
export interface ActionItemOption<TTarget extends { kind: string } = ActionTarget> {
  /** Rendered into `data-testid`, so the values are kebab-case like every other test id. */
  id: string;
  label: string;
  icon: RuiIcons;
  target: TTarget;
  /** silences the row for good, rather than leading somewhere */
  danger?: boolean;
}

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
  urgency: ActionUrgency;
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
  /** the row's lesser actions, in menu order; empty hides the menu */
  options: ActionItemOption<TTarget>[];
}

/** Rows gathered under one heading, the way the global center groups them by module. */
export interface ActionCenterSection<TTarget extends { kind: string } = ActionTarget> {
  /** Rendered into `data-testid`, so the values are kebab-case like every other test id. */
  id: string;
  title: string;
  items: ActionItem<TTarget>[];
}

/** The parts of a row that are the same for every item unless stated otherwise. */
export type ActionItemDefinition<TTarget extends { kind: string }, TId extends string = string> =
  Omit<ActionItem<TTarget, TId>, OptionalItemField>
  & Partial<Pick<ActionItem<TTarget, TId>, OptionalItemField>>;

type OptionalItemField = 'loading' | 'locked' | 'minimumTier' | 'informational' | 'checkTarget' | 'options';

/** The candidates holding a value, in order: how a center keeps only the rows and options that apply. */
export function applicable<T>(candidates: Option<T>[]): T[] {
  return flatMap(candidates, candidate => match(candidate, { none: (): T[] => [], some: (value): T[] => [value] }));
}

export function createActionItem<TTarget extends { kind: string }, TId extends string>(
  definition: ActionItemDefinition<TTarget, TId>,
): ActionItem<TTarget, TId> {
  return {
    checkTarget: definition.target,
    informational: false,
    loading: false,
    locked: false,
    minimumTier: null,
    options: [],
    ...definition,
  };
}
