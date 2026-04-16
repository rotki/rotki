import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { useAddressesNamesApi } from '@/modules/accounts/address-book/use-addresses-names-api';
import { useEnsOperations } from '@/modules/accounts/address-book/use-ens-operations';

vi.mock('@/modules/accounts/address-book/use-addresses-names-api', () => ({
  useAddressesNamesApi: vi.fn().mockReturnValue({
    getEnsNames: vi.fn().mockResolvedValue({}),
    getEnsNamesTask: vi.fn().mockResolvedValue({ taskId: 1 }),
    resolveEnsNames: vi.fn().mockResolvedValue(''),
  }),
}));

vi.mock('@/modules/accounts/address-book/use-address-name-resolution', () => ({
  useAddressNameResolution: vi.fn().mockReturnValue({
    updateEnsNamesAndReset: vi.fn(),
  }),
}));

vi.mock('@/modules/core/tasks/use-task-handler', () => ({
  isActionableFailure: vi.fn().mockReturnValue(false),
  useTaskHandler: vi.fn().mockReturnValue({
    runTask: vi.fn().mockResolvedValue({ success: false }),
  }),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn().mockReturnValue({
    notifyError: vi.fn(),
  }),
}));

describe('useEnsOperations', () => {
  let api: ReturnType<typeof useAddressesNamesApi>;
  let resolution: ReturnType<typeof useAddressNameResolution>;

  setActivePinia(createPinia());

  beforeEach(() => {
    api = useAddressesNamesApi();
    resolution = useAddressNameResolution();
    vi.clearAllMocks();
  });

  describe('fetchEnsNames', () => {
    it('should skip empty payload', async () => {
      const { fetchEnsNames } = useEnsOperations();
      await fetchEnsNames([]);

      expect(api.getEnsNames).not.toHaveBeenCalled();
    });

    it('should skip payload with no valid eth addresses', async () => {
      const { fetchEnsNames } = useEnsOperations();
      await fetchEnsNames([{ address: 'not-an-address', blockchain: null }]);

      expect(api.getEnsNames).not.toHaveBeenCalled();
    });

    it('should fetch ens names and update store', async () => {
      const address = '0x4585FE77225b41b697C938B01232131231231233';
      const result = { [address]: 'test.eth' };
      vi.mocked(api.getEnsNames).mockResolvedValue(result);

      const { fetchEnsNames } = useEnsOperations();
      await fetchEnsNames([{ address, blockchain: null }]);

      expect(api.getEnsNames).toHaveBeenCalledWith([address]);
      expect(resolution.updateEnsNamesAndReset).toHaveBeenCalledWith(result);
    });

    it('should deduplicate addresses', async () => {
      const address = '0x4585FE77225b41b697C938B01232131231231233';
      vi.mocked(api.getEnsNames).mockResolvedValue({});

      const { fetchEnsNames } = useEnsOperations();
      await fetchEnsNames([
        { address, blockchain: null },
        { address, blockchain: null },
      ]);

      expect(api.getEnsNames).toHaveBeenCalledWith([address]);
    });
  });

  describe('resolveEnsToAddress', () => {
    it('should return resolved address for valid ens name', async () => {
      const address = '0x4585FE77225b41b697C938B01232131231231233';
      vi.mocked(api.resolveEnsNames).mockResolvedValue(address);

      const { resolveEnsToAddress } = useEnsOperations();
      const result = await resolveEnsToAddress('test.eth');

      expect(result).toBe(address);
      expect(resolution.updateEnsNamesAndReset).toHaveBeenCalledWith({ [address]: 'test.eth' });
    });

    it('should return null for unresolvable ens name', async () => {
      vi.mocked(api.resolveEnsNames).mockResolvedValue('');

      const { resolveEnsToAddress } = useEnsOperations();
      const result = await resolveEnsToAddress('nonexistent.eth');

      expect(result).toBeNull();
      expect(resolution.updateEnsNamesAndReset).not.toHaveBeenCalled();
    });

    it('should return null for non-eth resolved address', async () => {
      vi.mocked(api.resolveEnsNames).mockResolvedValue('not-a-valid-address');

      const { resolveEnsToAddress } = useEnsOperations();
      const result = await resolveEnsToAddress('test.eth');

      expect(result).toBeNull();
      expect(resolution.updateEnsNamesAndReset).not.toHaveBeenCalled();
    });
  });
});
