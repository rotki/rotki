import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { handleResponse, validStatus } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';
import type { ActionResult } from '@rotki/common';
import type { PendingTask } from '@/types/task';

interface UseImportDataApiReturn {
  importDataFrom: (source: string, file: string, timestampFormat: string | null) => Promise<PendingTask>;
  importFile: (data: FormData) => Promise<PendingTask>;
}

export function useImportDataApi(): UseImportDataApiReturn {
  const importDataFrom = async (source: string, file: string, timestampFormat: string | null): Promise<PendingTask> => {
    const response = await api.instance.put<ActionResult<PendingTask>>(
      '/import',
      snakeCaseTransformer({
        source,
        file,
        timestampFormat,
        asyncQuery: true,
      }),
      {
        validateStatus: validStatus,
      },
    );

    return handleResponse(response);
  };

  const importFile = async (data: FormData): Promise<PendingTask> => {
    const response = await api.instance.post<ActionResult<PendingTask>>('/import', data, {
      validateStatus: validStatus,
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return handleResponse(response);
  };

  return {
    importDataFrom,
    importFile,
  };
}
