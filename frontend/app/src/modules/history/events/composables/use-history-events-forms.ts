import type { HistoryEventsTableEmitFn } from './types';
import type {
  HistoryEventEntry,
  StandaloneEditableEvents,
} from '@/types/history/events/schemas';
import { DIALOG_TYPES } from '@/components/history/events/dialog-types';

interface UseHistoryEventsFormsReturn {
  addEvent: (group: StandaloneEditableEvents, row: HistoryEventEntry) => void;
  editEvent: (event: any, row: HistoryEventEntry) => void;
  addMissingRule: (event: any, row: HistoryEventEntry) => void;
}

export function useHistoryEventsForms(
  suggestNextSequenceId: (group: HistoryEventEntry) => string,
  emit: HistoryEventsTableEmitFn,
): UseHistoryEventsFormsReturn {
  function addEvent(group: StandaloneEditableEvents, row: HistoryEventEntry): void {
    emit('show:dialog', {
      data: {
        group,
        nextSequenceId: suggestNextSequenceId(row),
        type: 'group-add',
      },
      type: DIALOG_TYPES.EVENT_FORM,
    });
  }

  function editEvent(event: any, row: HistoryEventEntry): void {
    emit('show:dialog', {
      data: {
        ...event,
        nextSequenceId: suggestNextSequenceId(row),
      },
      type: DIALOG_TYPES.EVENT_FORM,
    });
  }

  function addMissingRule($event: any, row: HistoryEventEntry): void {
    emit('show:dialog', {
      data: {
        ...$event,
        nextSequenceId: suggestNextSequenceId(row),
      },
      type: DIALOG_TYPES.MISSING_RULES,
    });
  }

  return {
    addEvent,
    addMissingRule,
    editEvent,
  };
}
