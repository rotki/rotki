import type { DeepReadonly, Ref } from 'vue';
import { fromAsync, type ResultAsync } from 'plainfp/result-async';
import { toRequestError } from '@/modules/core/api/request-result';
import { type LocationAliases, useLocationTreeApi } from '@/modules/locations/use-location-tree-api';

interface UseLocationAliasesReturn {
  aliases: DeepReadonly<Ref<LocationAliases>>;
  loading: Readonly<Ref<boolean>>;
  refreshAliases: () => ResultAsync<void, string>;
  saveAlias: (alias: string, locationIdentifier: string) => ResultAsync<void, string>;
  removeAlias: (alias: string) => ResultAsync<void, string>;
}

/** Whether two aliases name the same thing: the backend compares them without case. */
export function sameAlias(a: string, b: string): boolean {
  return a.toLowerCase() === b.toLowerCase();
}

/** The saved location aliases, kept up to date with each change the user makes. */
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
  }, cause => toRequestError(cause).message);

  /** The saved alias, which an alias with the same name in any case replaces, as the backend does. */
  const saveAlias = async (alias: string, locationIdentifier: string): ResultAsync<void, string> => fromAsync(async () => {
    const name = alias.trim();
    await api.setLocationAlias(name, locationIdentifier);
    set(aliases, [
      ...get(aliases).filter(entry => !sameAlias(entry.alias, name)),
      { alias: name, locationIdentifier },
    ]);
  }, cause => toRequestError(cause).message);

  const removeAlias = async (alias: string): ResultAsync<void, string> => fromAsync(async () => {
    await api.deleteLocationAlias(alias);
    set(aliases, get(aliases).filter(entry => !sameAlias(entry.alias, alias)));
  }, cause => toRequestError(cause).message);

  return {
    aliases: readonly(aliases),
    loading: readonly(loading),
    refreshAliases,
    removeAlias,
    saveAlias,
  };
}
