import { type ComputedRef } from 'vue';
import { type MaybeRef } from '@vueuse/core';
import { camelCase } from 'lodash-es';
import { type ProtocolMetadata } from '@/types/defi';
import { decodeHtmlEntities } from '@/utils/text';

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
    computed(() =>
      get(metadata).find(
        item => camelCase(item.identifier) === camelCase(get(identifier))
      )
    );

  const getDefiDataByName = (
    name: MaybeRef<string>
  ): ComputedRef<ProtocolMetadata | undefined> =>
    computed(() =>
      get(metadata).find(
        item => decodeHtmlEntities(item.name) === decodeHtmlEntities(get(name))
      )
    );

  const getDefiName = (identifier: MaybeRef<string>): ComputedRef<string> =>
    computed(() => get(getDefiData(identifier))?.name ?? get(identifier));

  const getDefiImage = (identifier: MaybeRef<string>): ComputedRef<string> =>
    computed(
      () => get(getDefiData(identifier))?.icon ?? `${get(identifier)}.svg`
    );

  const getDefiIdentifierByName = (
    name: MaybeRef<string>
  ): ComputedRef<string> =>
    computed(() => get(getDefiDataByName(name))?.identifier ?? get(name));

  return {
    metadata,
    getDefiData,
    getDefiName,
    getDefiImage,
    getDefiIdentifierByName
  };
});
