import { api } from '@/modules/core/api/rotki-api';
import { type PendingTask, PendingTaskSchema } from '@/modules/core/tasks/types';

interface ImportDataFromPayload {
  source: string;
  file: string;
  timestampFormat: string | null;
  timezone: string | null;
}

interface UseImportDataApiReturn {
  importDataFrom: (payload: ImportDataFromPayload) => Promise<PendingTask>;
  importFile: (data: FormData) => Promise<PendingTask>;
}

export function useImportDataApi(): UseImportDataApiReturn {
  const importDataFrom = async (payload: ImportDataFromPayload): Promise<PendingTask> => {
    const response = await api.put<PendingTask>(
      '/import',
      {
        asyncQuery: true,
        ...payload,
      },
    );

    return PendingTaskSchema.parse(response);
  };

  const importFile = async (data: FormData): Promise<PendingTask> => {
    const response = await api.post<PendingTask>('/import', data);

    return PendingTaskSchema.parse(response);
  };

  return {
    importDataFrom,
    importFile,
  };
}
