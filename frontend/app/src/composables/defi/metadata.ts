import type { MaybeRefOrGetter } from 'vue';
import type { ProtocolMetadata } from '@/modules/defi/types';
import { decodeHtmlEntities } from '@rotki/common';
import { camelCase } from 'es-toolkit';
import { useDefiApi } from '@/composables/api/defi';
import { useValueOrDefault } from '@/composables/utils/useValueOrDefault';
import { useMainStore } from '@/store/main';
import { getPublicProtocolImagePath } from '@/utils/file';

export const useDefiMetadata = createSharedComposable(() => {
  const { fetchDefiMetadata } = useDefiApi();

  const { connected } = storeToRefs(useMainStore());

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

  function findDefiData(identifier: string): ProtocolMetadata | undefined {
    return get(metadata).find(item => camelCase(item.identifier) === camelCase(identifier));
  }

  function findDefiDataByName(name: string): ProtocolMetadata | undefined {
    return get(metadata).find(item => decodeHtmlEntities(item.name) === decodeHtmlEntities(name));
  }

  const getDefiData = (identifier: MaybeRefOrGetter<string>): ComputedRef<ProtocolMetadata | undefined> =>
    computed<ProtocolMetadata | undefined>(() => findDefiData(toValue(identifier)));

  const getDefiName = (identifier: MaybeRefOrGetter<string>): ComputedRef<string> =>
    useValueOrDefault(
      computed<string | undefined>(() => {
        const data = findDefiData(toValue(identifier));
        return data?.name && decodeHtmlEntities(data.name);
      }),
      identifier,
    );

  const getDefiImageUrl = (identifier: string, icon: string | undefined): string => {
    const imageName = icon ?? `${identifier}.svg`;
    return getPublicProtocolImagePath(imageName);
  };

  function findDefiName(identifier: string): string {
    const data = findDefiData(identifier);
    return data?.name ? decodeHtmlEntities(data.name) : identifier;
  }

  function findDefiImage(identifier: string): string {
    return getDefiImageUrl(identifier, findDefiData(identifier)?.icon);
  }

  const getDefiImage = (identifier: MaybeRefOrGetter<string>): ComputedRef<string> =>
    computed<string>(() => findDefiImage(toValue(identifier)));

  const getDefiIdentifierByName = (name: MaybeRefOrGetter<string>): ComputedRef<string> =>
    useValueOrDefault(
      computed<string | undefined>(() => findDefiDataByName(toValue(name))?.identifier),
      name,
    );

  return {
    findDefiData,
    findDefiDataByName,
    findDefiImage,
    findDefiName,
    getDefiData,
    getDefiIdentifierByName,
    getDefiImage,
    getDefiImageUrl,
    getDefiName,
    loading,
    metadata,
  };
});
