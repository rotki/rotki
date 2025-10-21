import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useHistoryTransactionAccounts } from './use-history-transaction-accounts';

vi.mock('@/composables/info/chains', () => ({
  useSupportedChains: vi.fn(() => ({
    isBtcChains: vi.fn((chain: string) => ['btc', 'bch'].includes(chain)),
    isEvmLikeChains: vi.fn((chain: string) => chain === 'zksync_lite'),
    isSolanaChains: vi.fn(() => false),
    supportsTransactions: vi.fn((chain: string) =>
      ['eth', 'optimism', 'polygon_pos', 'arbitrum_one', 'avax', 'base', 'gnosis', 'scroll', 'binance_sc'].includes(chain),
    ),
  })),
}));

vi.mock('@/modules/balances/blockchain/use-account-addresses', () => ({
  useAccountAddresses: vi.fn(() => ({
    addresses: ref({
      arbitrum_one: ['0xbDA5747bFD65F08deb54cb465eB87D40e51B197E'],
      bch: ['qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6a'],
      btc: ['bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh', 'bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq'],
      eth: ['0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c', '0x71C7656EC7ab88b098defB751B7401B5f6d8976F'],
      optimism: ['0x8626f6940E2eb28930eFb4CeF49B2d1F2C9C1199'],
      polygon_pos: ['0xdD2FD4581271e230360230F9337D5c0430Bf44C0'],
      zksync_lite: ['0x2546BcD3c84621e976D8185a91A922aE77ECEc30'],
    }),
  })),
}));

describe('useHistoryTransactionAccounts', () => {
  let composable: ReturnType<typeof useHistoryTransactionAccounts>;

  beforeEach(() => {
    setActivePinia(createPinia());
    composable = useHistoryTransactionAccounts();
  });

  describe('getEvmAccounts', () => {
    it('should return all EVM accounts when no chains specified', () => {
      const accounts = composable.getEvmAccounts();

      expect(accounts).toHaveLength(5);
      expect(accounts).toContainEqual({ address: '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c', chain: 'eth' });
      expect(accounts).toContainEqual({ address: '0x71C7656EC7ab88b098defB751B7401B5f6d8976F', chain: 'eth' });
      expect(accounts).toContainEqual({ address: '0x8626f6940E2eb28930eFb4CeF49B2d1F2C9C1199', chain: 'optimism' });
      expect(accounts).toContainEqual({ address: '0xdD2FD4581271e230360230F9337D5c0430Bf44C0', chain: 'polygon_pos' });
      expect(accounts).toContainEqual({ address: '0xbDA5747bFD65F08deb54cb465eB87D40e51B197E', chain: 'arbitrum_one' });
    });

    it('should filter by specified chains', () => {
      const accounts = composable.getEvmAccounts(['eth', 'optimism']);

      expect(accounts).toHaveLength(3);
      expect(accounts).toContainEqual({ address: '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c', chain: 'eth' });
      expect(accounts).toContainEqual({ address: '0x71C7656EC7ab88b098defB751B7401B5f6d8976F', chain: 'eth' });
      expect(accounts).toContainEqual({ address: '0x8626f6940E2eb28930eFb4CeF49B2d1F2C9C1199', chain: 'optimism' });
      expect(accounts).not.toContainEqual({ address: '0xdD2FD4581271e230360230F9337D5c0430Bf44C0', chain: 'polygon_pos' });
    });

    it('should return empty array for non-EVM chains', () => {
      const accounts = composable.getEvmAccounts(['btc']);

      expect(accounts).toHaveLength(0);
    });

    it('should return all accounts when chains is empty array', () => {
      const accounts = composable.getEvmAccounts([]);

      expect(accounts).toHaveLength(5);
    });
  });

  describe('getEvmLikeAccounts', () => {
    it('should return all EVM-like accounts when no chains specified', () => {
      const accounts = composable.getEvmLikeAccounts();

      expect(accounts).toHaveLength(1);
      expect(accounts).toContainEqual({ address: '0x2546BcD3c84621e976D8185a91A922aE77ECEc30', chain: 'zksync_lite' });
    });

    it('should filter by specified chains', () => {
      const accounts = composable.getEvmLikeAccounts(['zksync_lite']);

      expect(accounts).toHaveLength(1);
      expect(accounts).toContainEqual({ address: '0x2546BcD3c84621e976D8185a91A922aE77ECEc30', chain: 'zksync_lite' });
    });

    it('should return empty array for non-EVM-like chains', () => {
      const accounts = composable.getEvmLikeAccounts(['eth']);

      expect(accounts).toHaveLength(0);
    });
  });

  describe('getBitcoinAccounts', () => {
    it('should return all Bitcoin accounts when no chains specified', () => {
      const accounts = composable.getBitcoinAccounts();

      expect(accounts).toHaveLength(3);
      expect(accounts).toContainEqual({ address: 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh', chain: 'btc' });
      expect(accounts).toContainEqual({ address: 'bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq', chain: 'btc' });
      expect(accounts).toContainEqual({ address: 'qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6a', chain: 'bch' });
    });

    it('should filter by specified chains', () => {
      const accounts = composable.getBitcoinAccounts(['btc']);

      expect(accounts).toHaveLength(2);
      expect(accounts).toContainEqual({ address: 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh', chain: 'btc' });
      expect(accounts).toContainEqual({ address: 'bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq', chain: 'btc' });
      expect(accounts).not.toContainEqual({ address: 'qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6a', chain: 'bch' });
    });

    it('should return empty array for non-Bitcoin chains', () => {
      const accounts = composable.getBitcoinAccounts(['eth']);

      expect(accounts).toHaveLength(0);
    });
  });

  describe('chain address format', () => {
    it('should return accounts in ChainAddress format', () => {
      const accounts = composable.getEvmAccounts(['eth']);

      expect(accounts).toHaveLength(2);

      accounts.forEach((account) => {
        expect(account).toHaveProperty('chain');
        expect(account).toHaveProperty('address');
        expect(typeof account.chain).toBe('string');
        expect(typeof account.address).toBe('string');
      });
    });
  });

  describe('multiple addresses per chain', () => {
    it('should handle multiple addresses for a single chain', () => {
      const btcAccounts = composable.getBitcoinAccounts(['btc']);
      const ethAccounts = composable.getEvmAccounts(['eth']);

      expect(btcAccounts).toHaveLength(2);
      expect(ethAccounts).toHaveLength(2);
    });
  });

  describe('cross-type exclusivity', () => {
    it('should not return Bitcoin accounts in EVM accounts', () => {
      const accounts = composable.getEvmAccounts();

      const btcAccount = accounts.find(acc => acc.chain === 'btc');
      expect(btcAccount).toBeUndefined();
    });

    it('should not return EVM accounts in Bitcoin accounts', () => {
      const accounts = composable.getBitcoinAccounts();

      const ethAccount = accounts.find(acc => acc.chain === 'eth');
      expect(ethAccount).toBeUndefined();
    });

    it('should not return EVM-like accounts in EVM accounts', () => {
      const accounts = composable.getEvmAccounts();

      const zksyncAccount = accounts.find(acc => acc.chain === 'zksync_lite');
      expect(zksyncAccount).toBeUndefined();
    });
  });
});
