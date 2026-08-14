import type { InjectionKey } from 'vue';
import type { UseHistoryEventsSelectionModeReturn } from '@/modules/history/events/use-selection-mode';

const HistoryEventsSelectionKey: InjectionKey<UseHistoryEventsSelectionModeReturn> = Symbol('history-events-selection');

/**
 * Shares the view's selection mode with the event rows that render checkboxes.
 *
 * Selection is owned by `HistoryEventsView` but only ever read at the leaves, so it is provided
 * rather than threaded through the table and the row switch. An embedding that has no selection
 * mode simply does not provide it, and the rows render without checkboxes.
 */
export function provideHistoryEventsSelection(selection: UseHistoryEventsSelectionModeReturn): void {
  provide(HistoryEventsSelectionKey, selection);
}

export function injectHistoryEventsSelection(): UseHistoryEventsSelectionModeReturn | undefined {
  return inject(HistoryEventsSelectionKey, undefined);
}
