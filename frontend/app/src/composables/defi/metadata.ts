import type { MaybeRefOrGetter } from 'vue';
import type { ProtocolMetadata } from '@/types/defi';
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

  const getDefiData = (identifier: MaybeRefOrGetter<string>): ComputedRef<ProtocolMetadata | undefined> =>
    useArrayFind(metadata, item => camelCase(item.identifier) === camelCase(toValue(identifier)));

  const getDefiDataByName = (name: MaybeRefOrGetter<string>): ComputedRef<ProtocolMetadata | undefined> =>
    useArrayFind<ProtocolMetadata>(metadata, item => decodeHtmlEntities(item.name) === decodeHtmlEntities(toValue(name)));

  const getDefiName = (identifier: MaybeRefOrGetter<string>): ComputedRef<string> =>
    useValueOrDefault(
      computed<string | undefined>(() => {
        const data = get(getDefiData(identifier));
        return data?.name && decodeHtmlEntities(data.name);
      }),
      identifier,
    );

  const getDefiImageUrl = (identifier: string, icon: string | undefined): string => {
    const imageName = icon ?? `${identifier}.svg`;
    return getPublicProtocolImagePath(imageName);
  };

  const getDefiImage = (identifier: MaybeRefOrGetter<string>): ComputedRef<string> =>
    computed(() => getDefiImageUrl(toValue(identifier), get(getDefiData(identifier))?.icon));

  const getDefiIdentifierByName = (name: MaybeRefOrGetter<string>): ComputedRef<string> =>
    useValueOrDefault(
      computed<string | undefined>(() => get(getDefiDataByName(name))?.identifier),
      name,
    );

  return {
    getDefiData,
    getDefiIdentifierByName,
    getDefiImage,
    getDefiImageUrl,
    getDefiName,
    loading,
    metadata,
  };
});
