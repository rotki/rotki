import type { ProtocolMetadata } from '@/types/defi';
import type { MaybeRef } from '@vueuse/core';
import { useDefiApi } from '@/composables/api/defi';
import { useRefMap } from '@/composables/utils/useRefMap';
import { useValueOrDefault } from '@/composables/utils/useValueOrDefault';
import { useMainStore } from '@/store/main';
import { camelCase } from 'es-toolkit';

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

  const getAirdropData = (identifier: MaybeRef<string>): ComputedRef<ProtocolMetadata | undefined> =>
    useArrayFind(metadata, item => camelCase(item.identifier) === camelCase(get(identifier)));

  const getAirdropName = (identifier: MaybeRef<string>): ComputedRef<string> =>
    useValueOrDefault(
      useRefMap(getAirdropData(identifier), i => i?.name),
      identifier,
    );

  const getAirdropImageUrl = (identifier: Ref<string>): ComputedRef<string> =>
    computed(() => {
      const data = get(getAirdropData(identifier));

      if (data?.iconUrl)
        return data.iconUrl;

      const image = data?.icon ?? `${transformCase(get(identifier), false)}.svg`;

      return `./assets/images/protocols/${image}`;
    });

  return {
    getAirdropImageUrl,
    getAirdropName,
    loading,
  };
});
