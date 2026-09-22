import type { DeepReadonly, Ref } from 'vue';
import { fromAsync, type ResultAsync } from 'plainfp/result-async';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { type LocationAliases, useLocationTreeApi } from '@/modules/locations/use-location-tree-api';

interface UseLocationAliasesReturn {
  aliases: DeepReadonly<Ref<LocationAliases>>;
  loading: Readonly<Ref<boolean>>;
  refreshAliases: () => ResultAsync<void, string>;
  saveAlias: (alias: string, locationIdentifier: string) => ResultAsync<void, string>;
  removeAlias: (alias: string) => ResultAsync<void, string>;
}

/** The saved location aliases, reloaded after every change. */
export function useLocationAliases(): UseLocationAliasesReturn {
  const aliases = ref<LocationAliases>([]);
  const loading = shallowRef<boolean>(false);

  const api = useLocationTreeApi();

  const refreshAliases = async (): ResultAsync<void, string> => fromAsync(async () => {
    set(loading, true);
    try {
      set(aliases, await api.fetchLocationAliases());
    }
    finally {
      set(loading, false);
    }
  }, cause => getErrorMessage(cause));

  const changing = async (change: () => Promise<boolean>): ResultAsync<void, string> => fromAsync(async () => {
    await change();
    set(aliases, await api.fetchLocationAliases());
  }, cause => getErrorMessage(cause));

  const saveAlias = async (alias: string, locationIdentifier: string): ResultAsync<void, string> =>
    changing(async () => api.setLocationAlias(alias.trim(), locationIdentifier));

  const removeAlias = async (alias: string): ResultAsync<void, string> =>
    changing(async () => api.deleteLocationAlias(alias));

  return {
    aliases: readonly(aliases),
    loading: readonly(loading),
    refreshAliases,
    removeAlias,
    saveAlias,
  };
}
