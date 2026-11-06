import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { MessageKey } from '@/message-key';
import type { MatchingFlow, PotentialMatchEntryLabels, UnmatchedEventGroup } from '@/modules/history/events/matching/types';
import type { UnmatchedFailure, UnmatchedRowActionSpec } from '@/modules/history/events/unmatched-actions';
import type { UnmatchedRow, UnmatchedVariant } from '@/modules/history/events/unmatched-row';
import type { PinnedName } from '@/modules/session/types';
import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';

/** A kind's unmatched and ignored items, and the backend calls that reload or auto-match them. */
interface MatchingKindSource<TItem> {
  unmatched: ComputedRef<TItem[]>;
  ignored: ComputedRef<TItem[]>;
  unmatchedError: Readonly<Ref<unknown>>;
  ignoredError: Readonly<Ref<unknown>>;
  loading: Readonly<Ref<boolean>>;
  ignoredLoading: Readonly<Ref<boolean>>;
  autoMatchLoading: ComputedRef<boolean>;
  autoMatchMinimumTier: Readonly<Ref<string | null>>;
  isAutoMatchAllowed: Readonly<Ref<boolean>>;
  refresh: () => Promise<void>;
  autoMatch: () => Promise<void>;
}

/** What a kind's panel can do to its items, one at a time or to the selection. */
interface MatchingKindActions<TItem> {
  actionFailure: Readonly<Ref<unknown>>;
  ignoreLoading: Readonly<Ref<boolean>>;
  modelSelectedIgnored: Ref<string[]>;
  modelSelectedUnmatched: Ref<string[]>;
  resolutionNotice: Readonly<Ref<{ message: string } | undefined>>;
  dismissResolution: () => void;
  ignore: (item: TItem) => Promise<void>;
  /** Ignores the selection, once its button asked. */
  ignoreSelected: () => Promise<void>;
  /** What ignoring the selection asks beside its button, counting it. */
  ignoreSelectedQuestion: Readonly<Ref<ConfirmQuestion>>;
  restore: (item: TItem) => Promise<void>;
  restoreSelected: () => Promise<void>;
  markExternal: (item: TItem) => Promise<void>;
  undoResolution: () => Promise<void>;
  /** Absent for a kind whose rows cannot create their missing counterpart; the row asks first. */
  createCounterpart?: (item: TItem) => Promise<void>;
  /**
   * Absent for a kind that has no fiat items to ignore at once. `ignoreAll` runs once its button
   * asked `question`.
   */
  fiat?: { items: ComputedRef<TItem[]>; ignoreAll: () => Promise<void>; question: Readonly<Ref<ConfirmQuestion>> };
}

interface MatchingKindRowsOptions<TItem> {
  /** The items to present, already filtered to unmatched or ignored by the caller. */
  items: MaybeRefOrGetter<TItem[]>;
  /** The rows are ignored ones, so restore replaces the resolution actions. */
  showRestore: MaybeRefOrGetter<boolean | undefined>;
  /** Matching is unavailable (no premium tier), so find-match is offered but disabled. */
  matchDisabled: MaybeRefOrGetter<boolean | undefined>;
  /** Why the last load of the items failed. */
  error: MaybeRefOrGetter<unknown>;
}

interface MatchingKindRows<TRow> {
  rows: ComputedRef<TRow[]>;
  description: ComputedRef<string>;
  /** Why the last load failed, shown in place of the empty text or above the rows it left. */
  failure: ComputedRef<UnmatchedFailure | undefined>;
  emptyDescription: ComputedRef<string>;
  specFor: (row: TRow) => UnmatchedRowActionSpec;
}

/**
 * Everything the shared matching panels need to know about one kind of unmatched item, so one
 * list, content, dialog and pinned panel serve both exchange asset movements and bridge legs.
 *
 * @remarks
 * A kind is a constant, not a composable: each `use*` member is a composable the panel that
 * needs it calls in its own setup, so a panel only builds the state it uses.
 *
 * `TRow` is the kind's own row, which its action specs read beyond the shared fields.
 */
export interface MatchingKind<TItem extends UnmatchedEventGroup, TRow extends UnmatchedRow<TItem> = UnmatchedRow<TItem>> {
  variant: UnmatchedVariant;
  pinnedName: PinnedName;
  messages: {
    title: MessageKey;
    actionFailed: MessageKey;
    autoMatchTooltip: MessageKey;
  };
  /** How the bulk ignore and restore buttons behave while nothing is selected or matching is gated. */
  bulkSelection: {
    /** Whether an empty selection hides the button rather than disabling it. */
    hideWhenEmpty: boolean;
    /** Whether the buttons need the auto-match tier, as the backend refuses them without it. */
    needsTier: boolean;
  };
  /** The event identifier the matching endpoints and the events table know an item by. */
  getIdentifier: (item: TItem) => number;
  useSource: () => MatchingKindSource<TItem>;
  useActions: (options: { onActionComplete?: () => Promise<void> }) => MatchingKindActions<TItem>;
  useRows: (options: MatchingKindRowsOptions<TItem>) => MatchingKindRows<TRow>;
  /** Undefined for a kind matched by the default asset movement calls. */
  useFlow: () => MatchingFlow | undefined;
  useEntryLabels: (subject: () => TItem | undefined) => ComputedRef<PotentialMatchEntryLabels | undefined>;
  useUnmatchableExplanation: (subject: () => TItem | undefined) => ComputedRef<string | undefined>;
}
