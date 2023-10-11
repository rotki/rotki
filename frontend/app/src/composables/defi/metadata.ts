import { type ComputedRef } from 'vue';
import { type MaybeRef } from '@vueuse/core';
import { camelCase } from 'lodash-es';
import { type ProtocolMetadata } from '@/types/defi';

export const useDefiMetadata = createSharedComposable(() => {
  const { fetchDefiMetadata } = useDefiApi();

  const { connected } = toRefs(useMainStore());

  const metadata: Ref<ProtocolMetadata[]> = asyncComputed<
    ProtocolMetadata[]
  >(() => {
    if (get(connected)) {
      return fetchDefiMetadata();
    }
    return [];
  }, []);

  const getDefiData = (
    identifier: MaybeRef<string>
  ): ComputedRef<ProtocolMetadata | undefined> =>
    useArrayFind(
      metadata,
      item => camelCase(item.identifier) === camelCase(get(identifier))
    );

  const getDefiDataByName = (
    name: MaybeRef<string>
  ): ComputedRef<ProtocolMetadata | undefined> =>
    useArrayFind<ProtocolMetadata>(
      metadata,
      item => decodeHtmlEntities(item.name) === decodeHtmlEntities(get(name))
    );

  const getDefiName = (identifier: MaybeRef<string>): ComputedRef<string> =>
    useValueOrDefault(
      useRefMap(getDefiData(identifier), i => i?.name),
      identifier
    );

  const getDefiImage = (identifier: MaybeRef<string>): ComputedRef<string> =>
    useValueOrDefault(
      useRefMap(getDefiData(identifier), i => i?.icon),
      computed(() => `${get(identifier)}.svg`)
    );

  const getDefiIdentifierByName = (
    name: MaybeRef<string>
  ): ComputedRef<string> =>
    useValueOrDefault(
      useRefMap(getDefiDataByName(name), i => i?.identifier),
      name
    );

  return {
    metadata,
    getDefiData,
    getDefiName,
    getDefiImage,
    getDefiIdentifierByName
  };
});
