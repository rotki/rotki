import type { ProtocolMetadata } from '@/modules/balances/protocols/types';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const connected = ref<boolean>(true);

const { spies } = vi.hoisted(() => ({
  spies: {
    fetchDefiMetadata: vi.fn(),
  },
}));

vi.mock('@/modules/airdrops/use-defi-api', () => ({
  useDefiApi: (): object => ({ fetchDefiMetadata: spies.fetchDefiMetadata }),
}));
vi.mock('@/modules/core/common/use-main-store', () => ({
  useMainStore: vi.fn(() => ({ connected })),
}));
vi.mock('@/modules/core/common/file/file', () => ({
  getPublicProtocolImagePath: (path: string): string => `img:${path}`,
}));

// createSharedComposable caches the instance, so reset the module per test.
async function load(): Promise<typeof import('./use-protocol-metadata')> {
  vi.resetModules();
  return import('./use-protocol-metadata');
}

const metadata: ProtocolMetadata[] = [
  { icon: 'aave.svg', identifier: 'aave', name: 'Aave' },
  { icon: 'uni.svg', identifier: 'uniswap-v2', name: 'Uniswap V2' },
];

describe('useProtocolMetadata', () => {
  beforeEach(() => {
    set(connected, true);
    spies.fetchDefiMetadata.mockResolvedValue(metadata);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should build a protocol image url from an icon or the identifier', async () => {
    const { useProtocolMetadata } = await load();
    const { getProtocolImageUrl } = useProtocolMetadata();
    expect(getProtocolImageUrl('aave', 'custom.png')).toBe('img:custom.png');
    expect(getProtocolImageUrl('aave', undefined)).toBe('img:aave.svg');
  });

  it('should load metadata when connected and look it up case-insensitively', async () => {
    const { useProtocolMetadata } = await load();
    const { findProtocolData } = useProtocolMetadata();
    await flushPromises();
    expect(spies.fetchDefiMetadata).toHaveBeenCalled();
    expect(findProtocolData('aave')?.name).toBe('Aave');
    // camelCase comparison ignores separators/casing
    expect(findProtocolData('uniswapV2')?.identifier).toBe('uniswap-v2');
    expect(findProtocolData('unknown')).toBeUndefined();
  });

  it('should not fetch metadata while disconnected', async () => {
    set(connected, false);
    const { useProtocolMetadata } = await load();
    const { findProtocolData, metadata: meta } = useProtocolMetadata();
    await flushPromises();
    expect(spies.fetchDefiMetadata).not.toHaveBeenCalled();
    expect(get(meta)).toEqual([]);
    expect(findProtocolData('aave')).toBeUndefined();
  });

  it('should resolve a protocol name and fall back to the identifier', async () => {
    const { useProtocolMetadata } = await load();
    const { findProtocolName } = useProtocolMetadata();
    await flushPromises();
    expect(findProtocolName('aave')).toBe('Aave');
    expect(findProtocolName('mystery')).toBe('mystery');
  });

  it('should look up a protocol identifier by name', async () => {
    const { useProtocolMetadata } = await load();
    const { getProtocolIdentifierByName } = useProtocolMetadata();
    await flushPromises();
    expect(get(getProtocolIdentifierByName('Aave'))).toBe('aave');
    expect(get(getProtocolIdentifierByName('Nope'))).toBe('Nope');
  });
});
