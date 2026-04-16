import type { MaybeRefOrGetter } from 'vue';
import type { ProtocolMetadata } from '@/modules/balances/protocols/types';
import { decodeHtmlEntities } from '@rotki/common';
import { camelCase } from 'es-toolkit';
import { useDefiApi } from '@/modules/airdrops/use-defi-api';
import { getPublicProtocolImagePath } from '@/modules/core/common/file/file';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { useValueOrDefault } from '@/modules/core/common/use-value-or-default';

export const useProtocolMetadata = createSharedComposable(() => {
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

  function findProtocolData(identifier: string): ProtocolMetadata | undefined {
    return get(metadata).find(item => camelCase(item.identifier) === camelCase(identifier));
  }

  function findProtocolDataByName(name: string): ProtocolMetadata | undefined {
    return get(metadata).find(item => decodeHtmlEntities(item.name) === decodeHtmlEntities(name));
  }

  const getProtocolData = (identifier: MaybeRefOrGetter<string>): ComputedRef<ProtocolMetadata | undefined> =>
    computed<ProtocolMetadata | undefined>(() => findProtocolData(toValue(identifier)));

  const getProtocolName = (identifier: MaybeRefOrGetter<string>): ComputedRef<string> =>
    useValueOrDefault(
      computed<string | undefined>(() => {
        const data = findProtocolData(toValue(identifier));
        return data?.name && decodeHtmlEntities(data.name);
      }),
      identifier,
    );

  const getProtocolImageUrl = (identifier: string, icon: string | undefined): string => {
    const imageName = icon ?? `${identifier}.svg`;
    return getPublicProtocolImagePath(imageName);
  };

  function findProtocolName(identifier: string): string {
    const data = findProtocolData(identifier);
    return data?.name ? decodeHtmlEntities(data.name) : identifier;
  }

  function findProtocolImage(identifier: string): string {
    return getProtocolImageUrl(identifier, findProtocolData(identifier)?.icon);
  }

  const getProtocolImage = (identifier: MaybeRefOrGetter<string>): ComputedRef<string> =>
    computed<string>(() => findProtocolImage(toValue(identifier)));

  const getProtocolIdentifierByName = (name: MaybeRefOrGetter<string>): ComputedRef<string> =>
    useValueOrDefault(
      computed<string | undefined>(() => findProtocolDataByName(toValue(name))?.identifier),
      name,
    );

  return {
    findProtocolData,
    findProtocolDataByName,
    findProtocolImage,
    findProtocolName,
    getProtocolData,
    getProtocolIdentifierByName,
    getProtocolImage,
    getProtocolImageUrl,
    getProtocolName,
    loading,
    metadata,
  };
});
