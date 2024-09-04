import { ProcessSkippedHistoryEventsResponse, SkippedHistoryEventsSummary } from '@/types/history/events';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus } from '@/services/utils';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import type { ActionStatus } from '@/types/action';
import type { ActionResult } from '@rotki/common';

interface UseSkippedHistoryEventsApiReturn {
  getSkippedEventsSummary: () => Promise<SkippedHistoryEventsSummary>;
  reProcessSkippedEvents: () => Promise<ProcessSkippedHistoryEventsResponse>;
  exportSkippedEventsCSV: (directoryPath: string) => Promise<boolean>;
  downloadSkippedEventsCSV: () => Promise<ActionStatus>;
}

export function useSkippedHistoryEventsApi(): UseSkippedHistoryEventsApiReturn {
  const getSkippedEventsSummary = async (): Promise<SkippedHistoryEventsSummary> => {
    const response = await api.instance.get<ActionResult<SkippedHistoryEventsSummary>>(
      '/history/skipped_external_events',
    );

    return SkippedHistoryEventsSummary.parse(handleResponse(response));
  };

  const reProcessSkippedEvents = async (): Promise<ProcessSkippedHistoryEventsResponse> => {
    const response = await api.instance.post<ActionResult<ProcessSkippedHistoryEventsResponse>>(
      '/history/skipped_external_events',
    );

    return ProcessSkippedHistoryEventsResponse.parse(handleResponse(response));
  };

  const exportSkippedEventsCSV = async (directoryPath: string): Promise<boolean> => {
    const response = await api.instance.put<ActionResult<boolean>>(
      '/history/skipped_external_events',
      snakeCaseTransformer({
        directoryPath,
      }),
      {
        validateStatus: validStatus,
      },
    );

    return handleResponse(response);
  };

  const downloadSkippedEventsCSV = async (): Promise<ActionStatus> => {
    try {
      const response = await api.instance.patch('/history/skipped_external_events', null, {
        responseType: 'blob',
        validateStatus: validStatus,
      });

      if (response.status === 200) {
        downloadFileByBlobResponse(response, 'skipped_external_events.csv');
        return { success: true };
      }

      const body = await (response.data as Blob).text();
      const result: ActionResult<null> = JSON.parse(body);

      return { success: false, message: result.message };
    }
    catch (error: any) {
      return { success: false, message: error.message };
    }
  };

  return {
    getSkippedEventsSummary,
    reProcessSkippedEvents,
    exportSkippedEventsCSV,
    downloadSkippedEventsCSV,
  };
}
