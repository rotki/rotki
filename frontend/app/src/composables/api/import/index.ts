import { type ActionResult } from '@rotki/common/lib/data';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { handleResponse, validStatus } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';
import { type PendingTask } from '@/types/task';

export const useImportDataApi = () => {
  const importDataFrom = async (
    source: string,
    file: string,
    timestampFormat: string | null
  ): Promise<PendingTask> => {
    const response = await api.instance.put<ActionResult<PendingTask>>(
      '/import',
      axiosSnakeCaseTransformer({
        source,
        file,
        timestampFormat,
        asyncQuery: true
      }),
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const importFile = async (data: FormData): Promise<PendingTask> => {
    const response = await api.instance.post<ActionResult<PendingTask>>(
      '/import',
      data,
      {
        validateStatus: validStatus,
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    );

    return handleResponse(response);
  };

  return {
    importDataFrom,
    importFile
  };
};
