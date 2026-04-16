import type { ActionStatus } from '@/modules/common/action';
import { api } from '@/modules/api/rotki-api';
import { downloadFileByUrl } from '@/modules/common/file/download';
import { getErrorMessage } from '@/modules/common/logging/error-handling';
import { ProcessSkippedHistoryEventsResponse, SkippedHistoryEventsSummary } from '@/modules/history/events/event-payloads';

interface UseSkippedHistoryEventsApiReturn {
  getSkippedEventsSummary: () => Promise<SkippedHistoryEventsSummary>;
  reProcessSkippedEvents: () => Promise<ProcessSkippedHistoryEventsResponse>;
  exportSkippedEventsCSV: (directoryPath: string) => Promise<boolean>;
  downloadSkippedEventsCSV: () => Promise<ActionStatus>;
}

export function useSkippedHistoryEventsApi(): UseSkippedHistoryEventsApiReturn {
  const getSkippedEventsSummary = async (): Promise<SkippedHistoryEventsSummary> => {
    const response = await api.get<SkippedHistoryEventsSummary>(
      '/history/skipped_external_events',
    );

    return SkippedHistoryEventsSummary.parse(response);
  };

  const reProcessSkippedEvents = async (): Promise<ProcessSkippedHistoryEventsResponse> => {
    const response = await api.post<ProcessSkippedHistoryEventsResponse>(
      '/history/skipped_external_events',
    );

    return ProcessSkippedHistoryEventsResponse.parse(response);
  };

  const exportSkippedEventsCSV = async (directoryPath: string): Promise<boolean> => api.put<boolean>(
    '/history/skipped_external_events',
    { directoryPath },
  );

  const downloadSkippedEventsCSV = async (): Promise<ActionStatus> => {
    try {
      const blob = await api.fetchBlob('/history/skipped_external_events', {
        method: 'PATCH',
      });

      const url = window.URL.createObjectURL(blob);
      downloadFileByUrl(url, 'skipped_external_events.csv');
      return { success: true };
    }
    catch (error: unknown) {
      return { message: getErrorMessage(error), success: false };
    }
  };

  return {
    downloadSkippedEventsCSV,
    exportSkippedEventsCSV,
    getSkippedEventsSummary,
    reProcessSkippedEvents,
  };
}
