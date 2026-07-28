/**
 * The actions a single unmatched row (or card) can offer. Both presentations emit one
 * typed action instead of a separate event each, so adding one does not mean threading
 * another emit through the list and the content component.
 */
export const UNMATCHED_ACTIONS = {
  CREATE_COUNTERPART: 'create-counterpart',
  FIND_MATCH: 'find-match',
  IGNORE: 'ignore',
  MARK_EXTERNAL: 'mark-external',
  RESTORE: 'restore',
  SHOW_IN_EVENTS: 'show-in-events',
} as const;

export type UnmatchedAction = typeof UNMATCHED_ACTIONS[keyof typeof UNMATCHED_ACTIONS];

/** What a list reports upwards: the action, and the row it was triggered on. */
export interface UnmatchedActionPayload<T> {
  action: UnmatchedAction;
  item: T;
}

/**
 * The in-place confirm for a reversible action. Reversible work (ignore, mark external)
 * asks here rather than in a modal; only genuinely destructive work keeps a dialog.
 * An action without an entry acts immediately - which is how a known-untracked row skips
 * the step for mark-external, since external is the only correct outcome there.
 */
export interface UnmatchedRowConfirm {
  /** One line, not a paragraph. */
  message: string;
  confirmLabel: string;
}

export type UnmatchedRowConfirms = Partial<Record<UnmatchedAction, UnmatchedRowConfirm>>;

export interface UnmatchedRowActionLabels {
  showInEventsTooltip: string;
  restore: string;
  restoreTooltip: string;
  findMatch: string;
  /** Used when the row promotes another action and find-match is demoted to the overflow. */
  findMatchAnyway: string;
  ignore: string;
  ignoreTooltip: string;
}

/**
 * An action that only some flows offer. Passing it is what renders the button, so its label can no
 * longer go missing the way a separate `show` flag plus an optional label allowed.
 */
export interface UnmatchedRowOptionalAction {
  label: string;
  tooltip: string;
  /** Renders the button filled, as the suggested resolution for the row. */
  emphasize?: boolean;
}

/**
 * Everything the action strip of one row needs, decided by the surface's model rather than
 * by whichever presentation happens to render it. Both layouts take this single object, so
 * a row cannot offer one set of actions as a card and a different set as a table row - the
 * way the direction badge once read "Bridge out" on a card and "DEPOSIT" in the dialog.
 */
export interface UnmatchedRowActionSpec {
  labels: UnmatchedRowActionLabels;
  /** Actions that ask in place before running; anything absent runs on click. */
  confirms?: UnmatchedRowConfirms;
  /** The row is already ignored, so restore replaces the resolution actions. */
  showRestore?: boolean;
  matchDisabled?: boolean;
  markExternal?: UnmatchedRowOptionalAction;
  createCounterpart?: UnmatchedRowOptionalAction;
}

/** How a row's actions are arranged. The strip is the only place this distinction lives. */
export const UNMATCHED_LAYOUTS = {
  /** Pinned width: one labelled primary, the rest as icons, the remainder in an overflow. */
  CARD: 'card',
  /** Dialog width: every action labelled on one line. */
  ROW: 'row',
} as const;

export type UnmatchedLayout = typeof UNMATCHED_LAYOUTS[keyof typeof UNMATCHED_LAYOUTS];
