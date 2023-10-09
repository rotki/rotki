import { type ComputedRef } from 'vue';
import { camelCase } from 'lodash-es';
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
    identifier: Ref<string>
  ): ComputedRef<ProtocolMetadata | undefined> =>
    computed(() =>
      get(metadata).find(
        item => camelCase(item.identifier) === camelCase(get(identifier))
      )
    );

  const getAirdropName = (identifier: Ref<string>): ComputedRef<string> =>
    computed(() => get(getAirdropData(identifier))?.name ?? get(identifier));

  const getAirdropImageUrl = (identifier: Ref<string>): ComputedRef<string> =>
    computed(() => {
      const image =
        get(getAirdropData(identifier))?.icon ?? `${get(identifier)}.svg`;

      if (!image) {
        return image;
      }

      return `./assets/images/protocols/${image}`;
    });

  return {
    getAirdropName,
    getAirdropImageUrl
  };
});
