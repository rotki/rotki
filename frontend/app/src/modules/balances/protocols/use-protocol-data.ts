import type { MaybeRefOrGetter, Ref } from 'vue';
import { toSentenceCase } from '@rotki/common';
import { useProtocolMetadata } from '@/modules/balances/protocols/use-protocol-metadata';
import { useLocations } from '@/modules/core/common/use-locations';
import { useHistoryEventCounterpartyMappings } from '@/modules/history/events/mapping/use-history-event-counterparty-mappings';

interface ImageProtocol { image: string; type: 'image'; name: string }

interface IconProtocol { icon: string; type: 'icon'; name: string }

type ProtocolData = ImageProtocol | IconProtocol | undefined;

interface UseProtocolDataReturn {
  protocolData: Readonly<Ref<ProtocolData>>;
}

export function useProtocolData(protocol: MaybeRefOrGetter<string>, isDark: MaybeRefOrGetter<boolean> = false): UseProtocolDataReturn {
  const { useLocationData } = useLocations();
  const { getProtocolData, getProtocolImageUrl } = useProtocolMetadata();
  const { getBaseCounterpartyData } = useHistoryEventCounterpartyMappings();

  const locationData = useLocationData(protocol);
  const defiData = getProtocolData(protocol);

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
      return { image: getProtocolImageUrl(protocolName, defi.icon), name: defi.name, type: 'image' };

    return undefined;
  });

  return {
    protocolData: readonly(protocolData),
  };
}
