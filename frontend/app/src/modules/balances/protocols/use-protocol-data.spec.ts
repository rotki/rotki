import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useProtocolData } from './use-protocol-data';

interface LocationInfo { name?: string; image?: string; icon?: string }

interface DefiInfo { icon: string; name: string }

interface CounterpartyInfo { image: string; label?: string }

const locationData = ref<LocationInfo | undefined>();
const defiData = ref<DefiInfo | undefined>();

const { spies } = vi.hoisted(() => ({
  spies: {
    getBaseCounterpartyData: vi.fn(),
    getProtocolImageUrl: vi.fn((name: string, icon: string) => `url:${name}:${icon}`),
  },
}));

vi.mock('@/modules/core/common/use-locations', () => ({
  useLocations: (): object => ({ useLocationData: () => locationData }),
}));
vi.mock('@/modules/balances/protocols/use-protocol-metadata', () => ({
  useProtocolMetadata: (): object => ({ getProtocolData: () => defiData, getProtocolImageUrl: spies.getProtocolImageUrl }),
}));
vi.mock('@/modules/history/events/mapping/use-history-event-counterparty-mappings', () => ({
  useHistoryEventCounterpartyMappings: (): object => ({ getBaseCounterpartyData: spies.getBaseCounterpartyData }),
}));

describe('useProtocolData', () => {
  beforeEach(() => {
    set(locationData, undefined);
    set(defiData, undefined);
    spies.getBaseCounterpartyData.mockReturnValue(undefined);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should render the wallet icon for the address pseudo-protocol', () => {
    const { protocolData } = useProtocolData('address');
    expect(get(protocolData)).toEqual({ icon: 'lu-wallet', name: 'Address', type: 'icon' });
  });

  it('should prefer a location image', () => {
    set(locationData, { image: 'kraken.svg', name: 'Kraken' });
    const { protocolData } = useProtocolData('kraken');
    expect(get(protocolData)).toEqual({ image: 'kraken.svg', name: 'Kraken', type: 'image' });
  });

  it('should fall back to a location icon and the display name', () => {
    set(locationData, { icon: 'lu-bank' });
    const { protocolData } = useProtocolData('somebank');
    expect(get(protocolData)).toEqual({ icon: 'lu-bank', name: 'Somebank', type: 'icon' });
  });

  it('should use counterparty data when there is no location', () => {
    spies.getBaseCounterpartyData.mockReturnValue({ image: 'uni.svg', label: 'Uniswap V3' } satisfies CounterpartyInfo);
    const { protocolData } = useProtocolData('uniswap-v3');
    expect(get(protocolData)).toEqual({ image: 'uni.svg', name: 'Uniswap V3', type: 'image' });
  });

  it('should build a defi protocol image url as a last resort', () => {
    set(defiData, { icon: 'aave.png', name: 'Aave' });
    const { protocolData } = useProtocolData('aave');
    expect(get(protocolData)).toEqual({ image: 'url:aave:aave.png', name: 'Aave', type: 'image' });
    expect(spies.getProtocolImageUrl).toHaveBeenCalledWith('aave', 'aave.png');
  });

  it('should return undefined when nothing matches', () => {
    const { protocolData } = useProtocolData('mystery');
    expect(get(protocolData)).toBeUndefined();
  });
});
