import type { MaybeRefOrGetter, Ref } from 'vue';
import { toSentenceCase } from '@rotki/common';
import { useDefiMetadata } from '@/composables/defi/metadata';
import { useHistoryEventCounterpartyMappings } from '@/composables/history/events/mapping/counterparty';
import { useLocations } from '@/composables/locations';

interface ImageProtocol { image: string; type: 'image'; name: string }

interface IconProtocol { icon: string; type: 'icon'; name: string }

type ProtocolData = ImageProtocol | IconProtocol | undefined;

interface UseProtocolDataReturn {
  protocolData: Readonly<Ref<ProtocolData>>;
}

export function useProtocolData(protocol: MaybeRefOrGetter<string>, isDark: MaybeRefOrGetter<boolean> = false): UseProtocolDataReturn {
  const { useLocationData } = useLocations();
  const { getDefiData, getDefiImageUrl } = useDefiMetadata();
  const { getBaseCounterpartyData } = useHistoryEventCounterpartyMappings();

  const locationData = useLocationData(protocol);
  const defiData = getDefiData(protocol);

  const protocolData = computed<ProtocolData>(() => {
    const protocolName = toValue(protocol);
    const displayName = toSentenceCase(protocolName);

    if (protocolName === 'address')
      return { icon: 'lu-wallet', name: displayName, type: 'icon' };

    const location = get(locationData);

    if (location) {
      const name = location.name ?? displayName;
      if (location.image)
        return { image: location.image, name, type: 'image' };

      if (location.icon)
        return { icon: location.icon, name, type: 'icon' };
    }

    const counterparty = getBaseCounterpartyData(protocolName, toValue(isDark));
    if (counterparty)
      return { image: counterparty.image, name: counterparty.label ?? displayName, type: 'image' };

    const defi = get(defiData);
    if (defi)
      return { image: getDefiImageUrl(protocolName, defi.icon), name: defi.name, type: 'image' };

    return undefined;
  });

  return {
    protocolData: readonly(protocolData),
  };
}
