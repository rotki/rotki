import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  validWithParamsSessionAndExternalService,
  validWithSessionAndExternalService,
} from '@/services/utils';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { type Watcher, Watchers } from '@/types/session';
import type { ActionResult } from '@rotki/common';

interface UseWatcherApiReturn {
  watchers: () => Promise<Watchers>;
  addWatcher: (watchers: Omit<Watcher, 'identifier'>[]) => Promise<Watchers>;
  editWatcher: (watchers: Watchers) => Promise<Watchers>;
  deleteWatcher: (identifiers: string[]) => Promise<Watchers>;
}

export function useWatchersApi(): UseWatcherApiReturn {
  const watchers = async (): Promise<Watchers> => {
    const response = await api.instance.get<ActionResult<Watchers>>('/watchers', {
      validateStatus: validWithSessionAndExternalService,
    });

    return Watchers.parse(handleResponse(response));
  };

  const addWatcher = async (watchers: Omit<Watcher, 'identifier'>[]): Promise<Watchers> => {
    const response = await api.instance.put<ActionResult<Watchers>>('/watchers', snakeCaseTransformer({ watchers }), {
      validateStatus: validWithParamsSessionAndExternalService,
    });

    return handleResponse(response);
  };

  const editWatcher = async (watchers: Watchers): Promise<Watchers> => {
    const response = await api.instance.patch<ActionResult<Watchers>>('/watchers', snakeCaseTransformer({ watchers }), {
      validateStatus: validWithParamsSessionAndExternalService,
    });

    return handleResponse(response);
  };

  const deleteWatcher = async (identifiers: string[]): Promise<Watchers> => {
    const response = await api.instance.delete<ActionResult<Watchers>>('/watchers', {
      data: snakeCaseTransformer({ watchers: identifiers }),
      validateStatus: validWithParamsSessionAndExternalService,
    });

    return handleResponse(response);
  };

  return {
    watchers,
    addWatcher,
    editWatcher,
    deleteWatcher,
  };
}
