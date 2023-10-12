import { type ComputedRef } from 'vue';
import { camelCase } from 'lodash-es';
import { type MaybeRef } from '@vueuse/core';
import { type ProtocolMetadata } from '@/types/defi';

export const useAirdropsMetadata = createSharedComposable(() => {
  const { fetchAirdropsMetadata } = useDefiApi();

  const { connected } = toRefs(useMainStore());

  const metadata: Ref<ProtocolMetadata[]> = asyncComputed<
    ProtocolMetadata[]
  >(() => {
    if (get(connected)) {
      return fetchAirdropsMetadata();
    }
    return [];
  }, []);

  const getAirdropData = (
    identifier: MaybeRef<string>
  ): ComputedRef<ProtocolMetadata | undefined> =>
    useArrayFind(
      metadata,
      item => camelCase(item.identifier) === camelCase(get(identifier))
    );

  const getAirdropName = (identifier: MaybeRef<string>): ComputedRef<string> =>
    useValueOrDefault(
      useRefMap(getAirdropData(identifier), i => i?.name),
      identifier
    );

  const getAirdropImageUrl = (identifier: Ref<string>): ComputedRef<string> =>
    computed(() => {
      const image =
        get(getAirdropData(identifier))?.icon ?? `${get(identifier)}.svg`;

      return `./assets/images/protocols/${image}`;
    });

  return {
    getAirdropName,
    getAirdropImageUrl
  };
});
