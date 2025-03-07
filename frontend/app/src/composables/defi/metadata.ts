import type { ProtocolMetadata } from '@/types/defi';
import type { MaybeRef } from '@vueuse/core';
import { useDefiApi } from '@/composables/api/defi';
import { useRefMap } from '@/composables/utils/useRefMap';
import { useValueOrDefault } from '@/composables/utils/useValueOrDefault';
import { useMainStore } from '@/store/main';
import { camelCase } from 'es-toolkit';

export const useDefiMetadata = createSharedComposable(() => {
  const { fetchDefiMetadata } = useDefiApi();

  const { connected } = toRefs(useMainStore());

  const loading = ref<boolean>(false);

  const metadata: Ref<ProtocolMetadata[]> = asyncComputed<ProtocolMetadata[]>(
    async () => {
      if (get(connected))
        return fetchDefiMetadata();

      return [];
    },
    [],
    { evaluating: loading },
  );

  const getDefiData = (identifier: MaybeRef<string>): ComputedRef<ProtocolMetadata | undefined> =>
    useArrayFind(metadata, item => camelCase(item.identifier) === camelCase(get(identifier)));

  const getDefiDataByName = (name: MaybeRef<string>): ComputedRef<ProtocolMetadata | undefined> =>
    useArrayFind<ProtocolMetadata>(metadata, item => decodeHtmlEntities(item.name) === decodeHtmlEntities(get(name)));

  const getDefiName = (identifier: MaybeRef<string>): ComputedRef<string> =>
    useValueOrDefault(
      useRefMap(getDefiData(identifier), i => i?.name && decodeHtmlEntities(i?.name)),
      identifier,
    );

  const getDefiImage = (identifier: MaybeRef<string>): ComputedRef<string> =>
    computed(() => {
      const imageName = get(getDefiData(identifier))?.icon || `${get(identifier)}.svg`;
      return `./assets/images/protocols/${imageName}`;
    });

  const getDefiIdentifierByName = (name: MaybeRef<string>): ComputedRef<string> =>
    useValueOrDefault(
      useRefMap(getDefiDataByName(name), i => i?.identifier),
      name,
    );

  return {
    getDefiData,
    getDefiIdentifierByName,
    getDefiImage,
    getDefiName,
    loading,
    metadata,
  };
});
