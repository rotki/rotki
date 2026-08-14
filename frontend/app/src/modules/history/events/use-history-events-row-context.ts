import type { ComputedRef, InjectionKey, Ref } from 'vue';
import type { DuplicateHandlingStatus, HighlightType } from '@/modules/history/events/action-types';
import type { LocationAndTxRef, PullEventPayload } from '@/modules/history/events/event-payloads';
import type { HistoryEventEntry, StandaloneEditableEvents } from '@/modules/history/events/schemas';
import type { HistoryEventDeletePayload, HistoryEventUnlinkPayload } from '@/modules/history/events/types';
import type { UseHistoryEventsSelectionModeReturn } from '@/modules/history/events/use-selection-mode';
import type { HistoryEventEditData } from '@/modules/history/management/forms/form-types';

/** Presentation state shared by every row, regardless of its kind. */
export interface HistoryEventsRowDisplay {
  /** Wide table row or narrow card, decided once from the viewport breakpoint. */
  variant: ComputedRef<'row' | 'card'>;
  hideActions: ComputedRef<boolean>;
  eventsLoading: Readonly<Ref<boolean>>;
  duplicateHandlingStatus: ComputedRef<DuplicateHandlingStatus | undefined>;
  selection: ComputedRef<UseHistoryEventsSelectionModeReturn | undefined>;
}

/** Reads into the loaded event data. All are map lookups, safe to call per row. */
export interface HistoryEventsRowLookups {
  groupEvents: (groupId: string) => HistoryEventEntry[];
  completeEventsForItem: (groupId: string, event: HistoryEventEntry) => HistoryEventEntry[];
  completeSubgroupEvents: (events: HistoryEventEntry[]) => HistoryEventEntry[];
  groupLocationLabel: (groupId: string) => string | undefined;
  /**
   * The group's ignored-asset state, or undefined when it has none to reveal and none revealed, in
   * which case the group row shows no indicator.
   */
  ignoredAssets: (groupId: string) => 'hidden' | 'showing' | undefined;
}

export interface HistoryEventsRowHighlight {
  isGroupHighlighted: (groupId: string) => boolean;
  isHighlighted: (event: HistoryEventEntry) => boolean;
  isSwapHighlighted: (events: HistoryEventEntry[]) => boolean;
  getHighlightType: (event: HistoryEventEntry) => HighlightType | undefined;
  getSwapHighlightType: (events: HistoryEventEntry[]) => HighlightType | undefined;
}

/** Everything a row can trigger. Each resolves its own group, so rows pass ids, not entries. */
export interface HistoryEventsRowActions {
  addEvent: (group: StandaloneEditableEvents, row: HistoryEventEntry) => void;
  editEvent: (data: HistoryEventEditData, groupId: string) => void;
  addMissingRule: (data: HistoryEventEditData, groupId: string) => void;
  deleteEvents: (payload: HistoryEventDeletePayload) => void;
  deleteTransaction: (payload: LocationAndTxRef) => void;
  unlinkEvent: (payload: HistoryEventUnlinkPayload) => void;
  unlinkGroup: (groupId: string) => void;
  toggleIgnore: (event: HistoryEventEntry) => Promise<void>;
  toggleShowIgnoredAssets: (groupId: string) => void;
  redecode: (payload: PullEventPayload, eventIdentifier: string) => void;
  redecodeWithOptions: (payload: PullEventPayload, groupIdentifier: string) => void;
  toggleSwapExpanded: (swapKey: string) => void;
  toggleMovementExpanded: (movementKey: string) => void;
  loadMore: (groupId: string) => void;
  refresh: () => void;
}

/**
 * What the virtual table hands down to its rows.
 *
 * Provided once by `HistoryEventsVirtualTable` and injected by `HistoryEventsVirtualRow`, so a row
 * takes only the `VirtualRow` it renders and nothing is drilled through the row switch.
 */
export interface HistoryEventsRowContext {
  display: HistoryEventsRowDisplay;
  lookups: HistoryEventsRowLookups;
  highlight: HistoryEventsRowHighlight;
  actions: HistoryEventsRowActions;
}

const HistoryEventsRowContextKey: InjectionKey<HistoryEventsRowContext> = Symbol('history-events-row-context');

export function provideHistoryEventsRowContext(context: HistoryEventsRowContext): void {
  provide(HistoryEventsRowContextKey, context);
}

export function injectHistoryEventsRowContext(): HistoryEventsRowContext {
  const context = inject(HistoryEventsRowContextKey);

  if (!context)
    throw new Error('History event rows must be rendered inside HistoryEventsVirtualTable');

  return context;
}
