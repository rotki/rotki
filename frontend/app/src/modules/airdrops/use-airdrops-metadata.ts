import type { MaybeRefOrGetter } from 'vue';
import type { ProtocolMetadata } from '@/modules/balances/protocols/types';
import { transformCase } from '@rotki/common';
import { camelCase } from 'es-toolkit';
import { useDefiApi } from '@/modules/airdrops/use-defi-api';
import { getPublicProtocolImagePath } from '@/modules/core/common/file/file';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { useValueOrDefault } from '@/modules/core/common/use-value-or-default';

export const useAirdropsMetadata = createSharedComposable(() => {
  const { fetchAirdropsMetadata } = useDefiApi();

  const { connected } = storeToRefs(useMainStore());
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

  function findAirdropData(identifier: string): ProtocolMetadata | undefined {
    return get(metadata).find(item => camelCase(item.identifier) === camelCase(identifier));
  }

  const getAirdropName = (identifier: MaybeRefOrGetter<string>): ComputedRef<string> =>
    useValueOrDefault(
      () => findAirdropData(toValue(identifier))?.name,
      identifier,
    );

  const getAirdropImageUrl = (identifier: MaybeRefOrGetter<string>): ComputedRef<string> =>
    computed<string>(() => {
      const data = findAirdropData(toValue(identifier));

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
