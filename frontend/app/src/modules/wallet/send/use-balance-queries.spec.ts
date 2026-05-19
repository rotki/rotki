import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useBalanceQueries } from '@/modules/wallet/send/use-balance-queries';

const addressesRef = ref<Record<string, string[]>>({});
const taskRunningRef = ref<boolean>(false);

vi.mock('@/modules/balances/blockchain/use-account-addresses', () => ({
  useAccountAddresses: vi.fn().mockImplementation(() => ({
    addresses: addressesRef,
    getAddresses: vi.fn(),
  })),
}));

vi.mock('@/modules/core/tasks/use-task-store', () => ({
  useTaskStore: vi.fn().mockImplementation(() => ({
    useIsTaskRunning: vi.fn().mockReturnValue(taskRunningRef),
  })),
}));

// Bypass the 200ms debounce in tests
vi.mock('@/modules/core/common/use-ref-debounce', () => ({
  useRefWithDebounce: vi.fn().mockImplementation((source: unknown) => source),
}));

describe('useBalanceQueries', () => {
  beforeEach(() => {
    set(addressesRef, {});
    set(taskRunningRef, false);
  });

  describe('useQueryingBalances', () => {
    it('should mirror the task-running ref', () => {
      const connected = ref(true);
      const address = ref<string | undefined>('0xabc');
      const { useQueryingBalances } = useBalanceQueries(connected, address);

      expect(get(useQueryingBalances)).toBe(false);
      set(taskRunningRef, true);
      expect(get(useQueryingBalances)).toBe(true);
    });
  });

  describe('warnUntrackedAddress', () => {
    it('should return false when not connected', () => {
      const connected = ref(false);
      const address = ref<string | undefined>('0xabc');
      const { warnUntrackedAddress } = useBalanceQueries(connected, address);

      expect(get(warnUntrackedAddress)).toBe(false);
    });

    it('should return false when connected address is missing or empty', () => {
      const connected = ref(true);
      const address = ref<string | undefined>(undefined);
      const { warnUntrackedAddress } = useBalanceQueries(connected, address);

      expect(get(warnUntrackedAddress)).toBe(false);

      set(address, '');
      expect(get(warnUntrackedAddress)).toBe(false);
    });

    it('should warn when connected address is not present in any tracked chain', () => {
      set(addressesRef, {
        eth: ['0x1', '0x2'],
        optimism: ['0x3'],
      });

      const connected = ref(true);
      const address = ref<string | undefined>('0xUNTRACKED');
      const { warnUntrackedAddress } = useBalanceQueries(connected, address);

      expect(get(warnUntrackedAddress)).toBe(true);
    });

    it('should not warn when connected address matches a tracked address on any chain', () => {
      set(addressesRef, {
        eth: ['0x1', '0x2'],
        optimism: ['0xMATCH'],
      });

      const connected = ref(true);
      const address = ref<string | undefined>('0xMATCH');
      const { warnUntrackedAddress } = useBalanceQueries(connected, address);

      expect(get(warnUntrackedAddress)).toBe(false);
    });

    it('should react to address changes', () => {
      set(addressesRef, { eth: ['0xKNOWN'] });
      const connected = ref(true);
      const address = ref<string | undefined>('0xKNOWN');
      const { warnUntrackedAddress } = useBalanceQueries(connected, address);

      expect(get(warnUntrackedAddress)).toBe(false);
      set(address, '0xOTHER');
      expect(get(warnUntrackedAddress)).toBe(true);
    });
  });
});
