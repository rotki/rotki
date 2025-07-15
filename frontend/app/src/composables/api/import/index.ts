import type { ActionResult } from '@rotki/common';
import type { PendingTask } from '@/types/task';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus } from '@/services/utils';

interface UseImportDataApiReturn {
  importDataFrom: (source: string, file: string, timestampFormat: string | null) => Promise<PendingTask>;
  importFile: (data: FormData) => Promise<PendingTask>;
}

export function useImportDataApi(): UseImportDataApiReturn {
  const importDataFrom = async (source: string, file: string, timestampFormat: string | null): Promise<PendingTask> => {
    const response = await api.instance.put<ActionResult<PendingTask>>(
      '/import',
      snakeCaseTransformer({
        asyncQuery: true,
        file,
        source,
        timestampFormat,
      }),
      {
        validateStatus: validStatus,
      },
    );

    return handleResponse(response);
  };

  const importFile = async (data: FormData): Promise<PendingTask> => {
    const response = await api.instance.post<ActionResult<PendingTask>>('/import', data, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  return {
    importDataFrom,
    importFile,
  };
}
