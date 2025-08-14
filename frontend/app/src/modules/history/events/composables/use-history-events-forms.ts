import type { HistoryEventsTableEmitFn } from './types';
import type {
  HistoryEventEntry,
  StandaloneEditableEvents,
} from '@/types/history/events/schemas';

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
    emit('show:form', {
      data: {
        group,
        nextSequenceId: suggestNextSequenceId(row),
        type: 'group-add',
      },
      type: 'event',
    });
  }

  function editEvent(event: any, row: HistoryEventEntry): void {
    emit('show:form', {
      data: {
        ...event,
        nextSequenceId: suggestNextSequenceId(row),
      },
      type: 'event',
    });
  }

  function addMissingRule($event: any, row: HistoryEventEntry): void {
    emit('show:form', {
      data: {
        ...$event,
        nextSequenceId: suggestNextSequenceId(row),
      },
      type: 'missingRule',
    });
  }

  return {
    addEvent,
    addMissingRule,
    editEvent,
  };
}
