import type { Accounts, BlockchainAccount } from '@/types/blockchain/accounts';
import type { RepullingTransactionPayload } from '@/types/history/events';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  getTimeRangeInDays,
  SECONDS_PER_DAY,
  shouldShowDateRangePicker,
  useRepullingTransactionForm,
} from './use-repulling-transaction-form';

function createMockAccount(address: string, chain: string): BlockchainAccount {
  return {
    chain,
    data: { address, type: 'address' },
    nativeAsset: 'ETH',
  };
}

const mockAccountsPerChain = ref<Accounts>({
  eth2: [
    createMockAccount('0x1234567890123456789012345678901234567890', 'eth2'),
  ],
  eth: [
    createMockAccount('0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c', 'eth'),
    createMockAccount('0x71C7656EC7ab88b098defB751B7401B5f6d8976F', 'eth'),
  ],
  optimism: [
    createMockAccount('0x8626f6940E2eb28930eFb4CeF49B2d1F2C9C1199', 'optimism'),
  ],
  arbitrum_one: [
    createMockAccount('0xbDA5747bFD65F08deb54cb465eB87D40e51B197E', 'arbitrum_one'),
  ],
});

const mockDecodableTxChainsInfo = ref([
  { id: 'eth' },
  { id: 'optimism' },
  { id: 'arbitrum_one' },
  { id: 'polygon_pos' },
]);

vi.mock('@/modules/accounts/use-blockchain-accounts-store', () => ({
  useBlockchainAccountsStore: vi.fn(() => ({
    accounts: mockAccountsPerChain,
  })),
}));

vi.mock('@/composables/info/chains', () => ({
  useSupportedChains: vi.fn(() => ({
    decodableTxChainsInfo: mockDecodableTxChainsInfo,
    getChain: vi.fn((chain: string) => chain),
  })),
}));

describe('use-repulling-transaction-form', () => {
  describe('shouldShowDateRangePicker', () => {
    it('should return true for blockchain type regardless of exchange', () => {
      expect(shouldShowDateRangePicker(true, undefined)).toBe(true);
      expect(shouldShowDateRangePicker(true, { location: 'coinbase' })).toBe(true);
      expect(shouldShowDateRangePicker(true, { location: 'kraken' })).toBe(true);
    });

    it('should return true when exchange is undefined for non-blockchain type', () => {
      expect(shouldShowDateRangePicker(false, undefined)).toBe(true);
    });

    it('should return false for exchanges without date range filter', () => {
      expect(shouldShowDateRangePicker(false, { location: 'coinbase' })).toBe(false);
      expect(shouldShowDateRangePicker(false, { location: 'binance' })).toBe(false);
      expect(shouldShowDateRangePicker(false, { location: 'binanceus' })).toBe(false);
      expect(shouldShowDateRangePicker(false, { location: 'bitmex' })).toBe(false);
    });

    it('should return true for exchanges with date range filter', () => {
      expect(shouldShowDateRangePicker(false, { location: 'kraken' })).toBe(true);
      expect(shouldShowDateRangePicker(false, { location: 'bitstamp' })).toBe(true);
      expect(shouldShowDateRangePicker(false, { location: 'bitfinex' })).toBe(true);
    });
  });

  describe('getTimeRangeInDays', () => {
    it('should return 0 when fromTimestamp is missing', () => {
      const data: RepullingTransactionPayload = {
        toTimestamp: 1704067200,
      };
      expect(getTimeRangeInDays(data)).toBe(0);
    });

    it('should return 0 when toTimestamp is missing', () => {
      const data: RepullingTransactionPayload = {
        fromTimestamp: 1704067200,
      };
      expect(getTimeRangeInDays(data)).toBe(0);
    });

    it('should return 0 when both timestamps are missing', () => {
      const data: RepullingTransactionPayload = {};
      expect(getTimeRangeInDays(data)).toBe(0);
    });

    it('should calculate correct days for exact day boundaries', () => {
      const data: RepullingTransactionPayload = {
        fromTimestamp: 1704067200, // 2024-01-01 00:00:00
        toTimestamp: 1704153600, // 2024-01-02 00:00:00 (exactly 1 day later)
      };
      expect(getTimeRangeInDays(data)).toBe(1);
    });

    it('should round up to next day for partial days', () => {
      const data: RepullingTransactionPayload = {
        fromTimestamp: 1704067200, // 2024-01-01 00:00:00
        toTimestamp: 1704067201, // Just 1 second later
      };
      expect(getTimeRangeInDays(data)).toBe(1);
    });

    it('should calculate correct days for 365 days', () => {
      const data: RepullingTransactionPayload = {
        fromTimestamp: 1704067200, // 2024-01-01
        toTimestamp: 1704067200 + (365 * SECONDS_PER_DAY),
      };
      expect(getTimeRangeInDays(data)).toBe(365);
    });

    it('should handle partial days by rounding up', () => {
      const data: RepullingTransactionPayload = {
        fromTimestamp: 1704067200,
        toTimestamp: 1704067200 + (1.5 * SECONDS_PER_DAY),
      };
      expect(getTimeRangeInDays(data)).toBe(2);
    });
  });

  describe('useRepullingTransactionForm', () => {
    beforeEach(() => {
      setActivePinia(createPinia());
      vi.clearAllMocks();

      // Reset mocks to default values
      set(mockAccountsPerChain, {
        eth2: [createMockAccount('0x1234567890123456789012345678901234567890', 'eth2')],
        eth: [
          createMockAccount('0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c', 'eth'),
          createMockAccount('0x71C7656EC7ab88b098defB751B7401B5f6d8976F', 'eth'),
        ],
        optimism: [createMockAccount('0x8626f6940E2eb28930eFb4CeF49B2d1F2C9C1199', 'optimism')],
        arbitrum_one: [createMockAccount('0xbDA5747bFD65F08deb54cb465eB87D40e51B197E', 'arbitrum_one')],
      });

      set(mockDecodableTxChainsInfo, [
        { id: 'eth' },
        { id: 'optimism' },
        { id: 'arbitrum_one' },
        { id: 'polygon_pos' },
      ]);
    });

    describe('chainOptions', () => {
      it('should return chains that have accounts and are decodable with all option first', () => {
        const { chainOptions } = useRepullingTransactionForm();

        expect(get(chainOptions)[0]).toBe('all');
        expect(get(chainOptions)).toContain('eth');
        expect(get(chainOptions)).toContain('optimism');
        expect(get(chainOptions)).toContain('arbitrum_one');
        expect(get(chainOptions)).not.toContain('polygon_pos');
      });

      it('should exclude chains with accounts that are not in decodable chains list', () => {
        const { chainOptions } = useRepullingTransactionForm();

        // eth2 has accounts but is not in mockDecodableTxChainsInfo
        expect(get(chainOptions)).not.toContain('eth2');
        // 3 chains + 'all' = 4
        expect(get(chainOptions)).toHaveLength(4);
      });

      it('should return empty array when no accounts', () => {
        set(mockAccountsPerChain, {});

        const { chainOptions } = useRepullingTransactionForm();

        expect(get(chainOptions)).toHaveLength(0);
      });

      it('should exclude chains with empty account arrays', () => {
        set(mockAccountsPerChain, {
          eth: [createMockAccount('0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c', 'eth')],
          optimism: [],
        });

        const { chainOptions } = useRepullingTransactionForm();

        expect(get(chainOptions)[0]).toBe('all');
        expect(get(chainOptions)).toContain('eth');
        expect(get(chainOptions)).not.toContain('optimism');
      });
    });

    describe('createDefaultFormData', () => {
      it('should return form data with all as default chain', () => {
        const { createDefaultFormData } = useRepullingTransactionForm();
        const formData = createDefaultFormData();

        expect(formData.chain).toBe('all');
        expect(formData.address).toBe('');
      });

      it('should return form data with timestamp range of 1 year', () => {
        const { createDefaultFormData } = useRepullingTransactionForm();
        const formData = createDefaultFormData();

        expect(formData.fromTimestamp).toBeDefined();
        expect(formData.toTimestamp).toBeDefined();

        const daysDiff = Math.round(
          (formData.toTimestamp! - formData.fromTimestamp!) / SECONDS_PER_DAY,
        );
        // Allow for slight variation due to dayjs processing
        expect(daysDiff).toBeGreaterThanOrEqual(364);
        expect(daysDiff).toBeLessThanOrEqual(366);
      });
    });

    describe('getUsableChains', () => {
      it('should return all chain options (excluding all) when chain is undefined', () => {
        const { chainOptions, getUsableChains } = useRepullingTransactionForm();
        const usableChains = getUsableChains(undefined);
        const expectedChains = get(chainOptions).filter(c => c !== 'all');

        expect(usableChains).toEqual(expectedChains);
        expect(usableChains).not.toContain('all');
      });

      it('should return all chain options (excluding all) when chain is all', () => {
        const { chainOptions, getUsableChains } = useRepullingTransactionForm();
        const usableChains = getUsableChains('all');
        const expectedChains = get(chainOptions).filter(c => c !== 'all');

        expect(usableChains).toEqual(expectedChains);
        expect(usableChains).not.toContain('all');
      });

      it('should return single chain array when chain is specified', () => {
        const { getUsableChains } = useRepullingTransactionForm();
        const usableChains = getUsableChains('eth');

        expect(usableChains).toEqual(['eth']);
      });
    });

    describe('shouldShowConfirmation', () => {
      it('should return false when accounts * days is below threshold', () => {
        const { shouldShowConfirmation } = useRepullingTransactionForm();

        // 1 account * 10 days = 10 < 180
        const data: RepullingTransactionPayload = {
          address: '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c',
          chain: 'eth',
          fromTimestamp: 1704067200,
          toTimestamp: 1704067200 + (10 * SECONDS_PER_DAY),
        };

        expect(shouldShowConfirmation(data)).toBe(false);
      });

      it('should return true when accounts * days is above threshold', () => {
        const { shouldShowConfirmation } = useRepullingTransactionForm();

        // 2 eth accounts * 100 days = 200 > 180
        const data: RepullingTransactionPayload = {
          chain: 'eth',
          fromTimestamp: 1704067200,
          toTimestamp: 1704067200 + (100 * SECONDS_PER_DAY),
        };

        expect(shouldShowConfirmation(data)).toBe(true);
      });

      it('should count all accounts across all chains when no chain specified', () => {
        const { shouldShowConfirmation } = useRepullingTransactionForm();

        // 4 total accounts * 50 days = 200 > 180
        const data: RepullingTransactionPayload = {
          fromTimestamp: 1704067200,
          toTimestamp: 1704067200 + (50 * SECONDS_PER_DAY),
        };

        expect(shouldShowConfirmation(data)).toBe(true);
      });

      it('should count all accounts across all chains when chain is all', () => {
        const { shouldShowConfirmation } = useRepullingTransactionForm();

        // 4 total accounts * 50 days = 200 > 180
        const data: RepullingTransactionPayload = {
          chain: 'all',
          fromTimestamp: 1704067200,
          toTimestamp: 1704067200 + (50 * SECONDS_PER_DAY),
        };

        expect(shouldShowConfirmation(data)).toBe(true);
      });

      it('should return false when no timestamps provided', () => {
        const { shouldShowConfirmation } = useRepullingTransactionForm();

        const data: RepullingTransactionPayload = {
          chain: 'eth',
        };

        expect(shouldShowConfirmation(data)).toBe(false);
      });

      it('should count 1 account when specific address is provided', () => {
        const { shouldShowConfirmation } = useRepullingTransactionForm();

        // 1 account * 100 days = 100 < 180
        const data: RepullingTransactionPayload = {
          address: '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c',
          chain: 'eth',
          fromTimestamp: 1704067200,
          toTimestamp: 1704067200 + (100 * SECONDS_PER_DAY),
        };

        expect(shouldShowConfirmation(data)).toBe(false);
      });

      it('should return true when single account exceeds threshold', () => {
        const { shouldShowConfirmation } = useRepullingTransactionForm();

        // 1 account * 200 days = 200 > 180
        const data: RepullingTransactionPayload = {
          address: '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c',
          chain: 'eth',
          fromTimestamp: 1704067200,
          toTimestamp: 1704067200 + (200 * SECONDS_PER_DAY),
        };

        expect(shouldShowConfirmation(data)).toBe(true);
      });

      it('should return false at exact threshold boundary', () => {
        const { shouldShowConfirmation } = useRepullingTransactionForm();

        // 2 eth accounts * 90 days = 180 (not > 180)
        const data: RepullingTransactionPayload = {
          chain: 'eth',
          fromTimestamp: 1704067200,
          toTimestamp: 1704067200 + (90 * SECONDS_PER_DAY),
        };

        expect(shouldShowConfirmation(data)).toBe(false);
      });

      it('should return true just above threshold boundary', () => {
        const { shouldShowConfirmation } = useRepullingTransactionForm();

        // 2 eth accounts * 91 days = 182 > 180
        const data: RepullingTransactionPayload = {
          chain: 'eth',
          fromTimestamp: 1704067200,
          toTimestamp: 1704067200 + (91 * SECONDS_PER_DAY),
        };

        expect(shouldShowConfirmation(data)).toBe(true);
      });
    });
  });
});
