import { api } from '@/modules/api/rotki-api';
import { type PendingTask, PendingTaskSchema } from '@/types/task';

interface UseImportDataApiReturn {
  importDataFrom: (source: string, file: string, timestampFormat: string | null) => Promise<PendingTask>;
  importFile: (data: FormData) => Promise<PendingTask>;
}

export function useImportDataApi(): UseImportDataApiReturn {
  const importDataFrom = async (source: string, file: string, timestampFormat: string | null): Promise<PendingTask> => {
    const response = await api.put<PendingTask>(
      '/import',
      {
        asyncQuery: true,
        file,
        source,
        timestampFormat,
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
