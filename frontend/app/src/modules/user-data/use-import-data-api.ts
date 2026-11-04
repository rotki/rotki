import { api } from '@/modules/core/api/rotki-api';
import { type PendingTask, PendingTaskSchema } from '@/modules/core/tasks/types';
import { ImportLocationPreflightSchema, type ImportLocationResolution } from './import-location-types';

interface ImportLocationPreflightPayload {
  source: string;
  file: string;
  locationMappings?: Record<string, string>;
}

interface ImportDataFromPayload {
  source: string;
  file: string;
  timestampFormat: string | null;
  timezone: string | null;
  locationMappings?: Record<string, string>;
}

/** The keys of `locationMappings` are values from the user's file, which the backend must get verbatim. */
const SKIP_SNAKE_CASE_MAPPINGS = ['locationMappings'];

interface UseImportDataApiReturn {
  checkImportLocations: (payload: ImportLocationPreflightPayload) => Promise<ImportLocationResolution[]>;
  checkImportFileLocations: (data: FormData) => Promise<ImportLocationResolution[]>;
  importDataFrom: (payload: ImportDataFromPayload) => Promise<PendingTask>;
  importFile: (data: FormData) => Promise<PendingTask>;
}

export function useImportDataApi(): UseImportDataApiReturn {
  const checkImportLocations = async (payload: ImportLocationPreflightPayload): Promise<ImportLocationResolution[]> => {
    const response = await api.put('/import/preflight', payload, { skipSnakeCase: SKIP_SNAKE_CASE_MAPPINGS });
    return ImportLocationPreflightSchema.parse(response).locations;
  };

  const checkImportFileLocations = async (data: FormData): Promise<ImportLocationResolution[]> => {
    const response = await api.post('/import/preflight', data);
    return ImportLocationPreflightSchema.parse(response).locations;
  };

  const importDataFrom = async (payload: ImportDataFromPayload): Promise<PendingTask> => {
    const response = await api.put<PendingTask>(
      '/import',
      {
        asyncQuery: true,
        ...payload,
      },
      { skipSnakeCase: SKIP_SNAKE_CASE_MAPPINGS },
    );

    return PendingTaskSchema.parse(response);
  };

  const importFile = async (data: FormData): Promise<PendingTask> => {
    const response = await api.post<PendingTask>('/import', data);

    return PendingTaskSchema.parse(response);
  };

  return {
    checkImportLocations,
    checkImportFileLocations,
    importDataFrom,
    importFile,
  };
}
