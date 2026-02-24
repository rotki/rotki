import type { MaybeRefOrGetter } from 'vue';
import type { ProtocolMetadata } from '@/types/defi';
import { transformCase } from '@rotki/common';
import { camelCase } from 'es-toolkit';
import { useDefiApi } from '@/composables/api/defi';
import { useRefMap } from '@/composables/utils/useRefMap';
import { useValueOrDefault } from '@/composables/utils/useValueOrDefault';
import { useMainStore } from '@/store/main';
import { getPublicProtocolImagePath } from '@/utils/file';

export const useAirdropsMetadata = createSharedComposable(() => {
  const { fetchAirdropsMetadata } = useDefiApi();

  const { connected } = toRefs(useMainStore());
  const loading = ref<boolean>(false);

  const metadata: Ref<ProtocolMetadata[]> = asyncComputed<ProtocolMetadata[]>(
    async () => {
      if (get(connected))
        return fetchAirdropsMetadata();

      return [];
    },
    [],
    { evaluating: loading },
  );

  const getAirdropData = (identifier: MaybeRefOrGetter<string>): ComputedRef<ProtocolMetadata | undefined> =>
    useArrayFind(metadata, item => camelCase(item.identifier) === camelCase(toValue(identifier)));

  const getAirdropName = (identifier: MaybeRefOrGetter<string>): ComputedRef<string> =>
    useValueOrDefault(
      useRefMap(getAirdropData(identifier), i => i?.name),
      identifier,
    );

  const getAirdropImageUrl = (identifier: MaybeRefOrGetter<string>): ComputedRef<string> =>
    computed(() => {
      const data = get(getAirdropData(identifier));

      if (data?.iconUrl)
        return data.iconUrl;

      const image = data?.icon ?? `${transformCase(toValue(identifier), false)}.svg`;

      return getPublicProtocolImagePath(image);
    });

  return {
    getAirdropImageUrl,
    getAirdropName,
    loading,
  };
});
