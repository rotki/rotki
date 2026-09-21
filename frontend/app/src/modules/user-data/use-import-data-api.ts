import { z } from 'zod';
import { api } from '@/modules/core/api/rotki-api';
import { type PendingTask, PendingTaskSchema } from '@/modules/core/tasks/types';

interface ImportDataFromPayload {
  source: string;
  file: string;
  timestampFormat: string | null;
  timezone: string | null;
  /**
   * Location values of the file mapped to location identifiers, as a JSON string.
   *
   * @remarks
   * Sent as a string because the values are the file's own spelling: the request body's keys are
   * converted to snake case, which would rename them.
   */
  locationMappings?: string;
}

/** What a location value of an imported file resolves to, as the import preflight reports it. */
const ImportLocationResolution = z.object({
  value: z.string(),
  status: z.enum(['resolved', 'ambiguous', 'unresolved']),
  location: z.string().nullable(),
  candidates: z.array(z.string()),
});

export type ImportLocationResolution = z.infer<typeof ImportLocationResolution>;

const ImportPreflightResult = z.object({ locations: z.array(ImportLocationResolution) });

interface UseImportDataApiReturn {
  importDataFrom: (payload: ImportDataFromPayload) => Promise<PendingTask>;
  importFile: (data: FormData) => Promise<PendingTask>;
  preflightImport: (payload: { source: string; file: string }) => Promise<ImportLocationResolution[]>;
  preflightImportFile: (data: FormData) => Promise<ImportLocationResolution[]>;
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

  const preflightImport = async (payload: { source: string; file: string }): Promise<ImportLocationResolution[]> =>
    ImportPreflightResult.parse(await api.put<unknown>('/import/preflight', payload)).locations;

  const preflightImportFile = async (data: FormData): Promise<ImportLocationResolution[]> =>
    ImportPreflightResult.parse(await api.post<unknown>('/import/preflight', data)).locations;

  return {
    importDataFrom,
    importFile,
    preflightImport,
    preflightImportFile,
  };
}
