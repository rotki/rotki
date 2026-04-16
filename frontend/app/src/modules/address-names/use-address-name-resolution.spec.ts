import type { AddressBookEntry } from '@/modules/address-names/eth-names';
import { Blockchain } from '@rotki/common';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAddressesNamesApi } from '@/composables/api/blockchain/addresses-names';
import { useAddressNameResolution } from '@/modules/address-names/use-address-name-resolution';
import { useAddressNamesStore } from '@/modules/address-names/use-address-names-store';
import { getDefaultFrontendSettings } from '@/modules/settings/types/frontend-settings';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';

vi.mock('@/composables/api/blockchain/addresses-names', () => ({
  useAddressesNamesApi: vi.fn().mockReturnValue({
    ensAvatarUrl: vi.fn().mockImplementation((ens: string, _ts?: number): string => `https://avatar/${ens}`),
    getAddressesNames: vi.fn().mockResolvedValue([]),
  }),
}));

vi.mock('@/composables/info/chains', async () => {
  const { ref } = await import('vue');
  return {
    useSupportedChains: vi.fn().mockReturnValue({
      supportedChains: ref([
        { id: 'eth', type: 'evm' },
        { id: 'optimism', type: 'evm' },
      ]),
    }),
  };
});

function enableAliasNames(enabled: boolean): void {
  useFrontendSettingsStore().update({
    ...getDefaultFrontendSettings(),
    enableAliasNames: enabled,
  });
}

describe('useAddressNameResolution', () => {
  let resolution: ReturnType<typeof useAddressNameResolution>;
  let api: ReturnType<typeof useAddressesNamesApi>;
  setActivePinia(createPinia());

  beforeEach(() => {
    vi.useFakeTimers();
    resolution = useAddressNameResolution();
    api = useAddressesNamesApi();
    resolution.resetAddressesNames();
    // Reset ENS names state from previous tests
    const store = useAddressNamesStore();
    const { ensNames } = storeToRefs(store);
    set(ensNames, {});
    vi.clearAllMocks();
  });

  describe('useAddressName', () => {
    const mockedResult: AddressBookEntry[] = [
      {
        address: '0x4585FE77225b41b697C938B01232131231231233',
        blockchain: Blockchain.ETH,
        name: 'test_name',
      },
      {
        address: '0x4585FE77225b41b697C938B01232131231231231',
        blockchain: Blockchain.ETH,
        name: 'test1.eth',
      },
    ];

    it('should resolve address names when enableAliasNames is true', async () => {
      enableAliasNames(true);
      vi.mocked(api.getAddressesNames).mockResolvedValue(mockedResult);

      const firstName = resolution.useAddressName(() => '0x4585FE77225b41b697C938B01232131231231233');
      const secondName = resolution.useAddressName(() => '0x4585FE77225b41b697C938B01232131231231231');

      expect(get(firstName)).toBeUndefined();
      expect(get(secondName)).toBeUndefined();

      vi.advanceTimersByTime(2500);
      await flushPromises();

      expect(api.getAddressesNames).toHaveBeenCalledOnce();
      expect(get(firstName)).toBe('test_name');
      expect(get(secondName)).toBe('test1.eth');
    });

    it('should not match API result with null blockchain against a valid chain key', async () => {
      enableAliasNames(true);

      const address = '0xAA00000000000000000000000000000000000001';
      vi.mocked(api.getAddressesNames).mockResolvedValue([
        { address, blockchain: null, name: 'multi_chain_name' },
      ]);

      const addressName = resolution.useAddressName(() => address, () => Blockchain.ETH);

      expect(get(addressName)).toBeUndefined();
      vi.advanceTimersByTime(2500);
      await flushPromises();

      expect(api.getAddressesNames).toHaveBeenCalledOnce();
      expect(get(addressName)).toBeUndefined();
    });

    it('should match API result when blockchain matches the queried chain', async () => {
      enableAliasNames(true);

      const address = '0xBB00000000000000000000000000000000000002';
      vi.mocked(api.getAddressesNames).mockResolvedValue([
        { address, blockchain: Blockchain.ETH, name: 'eth_name' },
      ]);

      const addressName = resolution.useAddressName(() => address, () => Blockchain.ETH);

      expect(get(addressName)).toBeUndefined();
      vi.advanceTimersByTime(2500);
      await flushPromises();

      expect(get(addressName)).toBe('eth_name');
    });

    it('should return undefined when enableAliasNames is false', async () => {
      enableAliasNames(false);
      vi.mocked(api.getAddressesNames).mockResolvedValue(mockedResult);

      const firstName = resolution.useAddressName(() => '0x4585FE77225b41b697C938B01232131231231233');
      const secondName = resolution.useAddressName(() => '0x4585FE77225b41b697C938B01232131231231231');

      vi.advanceTimersByTime(2500);
      await flushPromises();

      expect(api.getAddressesNames).not.toHaveBeenCalled();
      expect(get(firstName)).toBeUndefined();
      expect(get(secondName)).toBeUndefined();
    });
  });

  describe('getAddressName', () => {
    it('should return undefined when cache is not populated', () => {
      enableAliasNames(true);
      expect(resolution.getAddressName('0xCC00000000000000000000000000000000000003')).toBeUndefined();
    });

    it('should return undefined when enableAliasNames is false', () => {
      enableAliasNames(false);
      expect(resolution.getAddressName('0xCC00000000000000000000000000000000000003')).toBeUndefined();
    });

    it('should return undefined for ETH2 blockchain', () => {
      enableAliasNames(true);
      expect(resolution.getAddressName('0xCC00000000000000000000000000000000000003', Blockchain.ETH2)).toBeUndefined();
    });

    it('should return undefined for empty address', () => {
      enableAliasNames(true);
      expect(resolution.getAddressName('')).toBeUndefined();
    });
  });

  describe('getEnsName', () => {
    it('should return ens name when present in store', () => {
      enableAliasNames(true);
      const store = useAddressNamesStore();
      store.setEnsNames({ '0xAddr1': 'test.eth' });

      expect(resolution.getEnsName('0xAddr1')).toBe('test.eth');
    });

    it('should return null when ens name not in store', () => {
      enableAliasNames(true);
      expect(resolution.getEnsName('0xAddr1')).toBeNull();
    });

    it('should return null when enableAliasNames is false', () => {
      enableAliasNames(false);
      const store = useAddressNamesStore();
      store.setEnsNames({ '0xAddr1': 'test.eth' });

      expect(resolution.getEnsName('0xAddr1')).toBeNull();
    });
  });

  describe('useEnsAvatarUrl', () => {
    it('should return avatar url when ens name exists', () => {
      enableAliasNames(true);
      const store = useAddressNamesStore();
      store.setEnsNames({ '0xAddr1': 'test.eth' });

      const avatarUrl = resolution.useEnsAvatarUrl(() => '0xAddr1');
      expect(get(avatarUrl)).toBe('https://avatar/test.eth');
    });

    it('should return null when no ens name', () => {
      enableAliasNames(true);
      const avatarUrl = resolution.useEnsAvatarUrl(() => '0xUnknown');
      expect(get(avatarUrl)).toBeNull();
    });
  });

  describe('useEnsNamesList', () => {
    it('should return list of non-null ens names', () => {
      const store = useAddressNamesStore();
      store.setEnsNames({
        '0xAddr1': 'one.eth',
        '0xAddr2': null,
        '0xAddr3': 'three.eth',
      });

      const list = resolution.useEnsNamesList();
      expect(get(list)).toStrictEqual(['one.eth', 'three.eth']);
    });

    it('should return empty list when no ens names', () => {
      const list = resolution.useEnsNamesList();
      expect(get(list)).toStrictEqual([]);
    });
  });

  describe('updateEnsNamesAndReset', () => {
    it('should update ens names in store', () => {
      const store = useAddressNamesStore();
      resolution.updateEnsNamesAndReset({ '0xAddr1': 'new.eth' });

      const { ensNames } = storeToRefs(store);
      expect(get(ensNames)['0xAddr1']).toBe('new.eth');
    });

    it('should not reset cache when values are unchanged', () => {
      const store = useAddressNamesStore();
      store.setEnsNames({ '0xAddr1': 'same.eth' });

      // Calling with the same value should not trigger cache invalidation
      // We verify by checking the function doesn't throw and completes
      resolution.updateEnsNamesAndReset({ '0xAddr1': 'same.eth' });

      const { ensNames } = storeToRefs(store);
      expect(get(ensNames)['0xAddr1']).toBe('same.eth');
    });
  });

  describe('useAddressesWithoutNames', () => {
    it('should return empty when no unknown entries exist', () => {
      const result = resolution.useAddressesWithoutNames();
      expect(get(result)).toStrictEqual([]);
    });
  });
});
