import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef } from 'vue';
import { useDefiMetadata } from '@/composables/defi/metadata';
import { useHistoryEventCounterpartyMappings } from '@/composables/history/events/mapping/counterparty';
import { useLocations } from '@/composables/locations';
import { toSentenceCase } from '@rotki/common';

interface ImageProtocol { image: string; type: 'image'; name: string }

interface IconProtocol { icon: string; type: 'icon'; name: string }

type ProtocolData = ImageProtocol | IconProtocol | undefined;

interface UseProtocolDataReturn { protocolData: ComputedRef<ProtocolData> }

export function useProtocolData(protocol: MaybeRef<string>, isDark: MaybeRef<boolean> = false): UseProtocolDataReturn {
  const { locationData: useLocationData } = useLocations();
  const { getDefiData, getDefiImageUrl } = useDefiMetadata();
  const { getBaseCounterpartyData } = useHistoryEventCounterpartyMappings();

  const locationData = useLocationData(protocol);
  const defiData = getDefiData(protocol);

  const protocolData = computed<ProtocolData>(() => {
    const name = get(protocol);
    const formattedName = toSentenceCase(name);
    if (name === 'address') {
      return {
        icon: 'lu-wallet',
        name: formattedName,
        type: 'icon',
      };
    }

    const location = get(locationData);

    if (location && (location.image || location.icon)) {
      if (location.image) {
        return {
          image: location.image,
          name: location.name ?? formattedName,
          type: 'image',
        };
      }
      else if (location.icon) {
        return {
          icon: location.icon,
          name: location.name ?? formattedName,
          type: 'icon',
        };
      }
    }

    const counterparty = getBaseCounterpartyData(name, get(isDark));
    if (counterparty) {
      return {
        image: counterparty.image,
        name: counterparty.label ?? formattedName,
        type: 'image',
      };
    }

    const defi = get(defiData);
    if (defi) {
      return {
        image: getDefiImageUrl(name, defi.icon),
        name: defi.name,
        type: 'image',
      };
    }

    return undefined;
  });

  return {
    protocolData,
  };
}
