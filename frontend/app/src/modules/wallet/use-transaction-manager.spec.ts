import type { TransactionParams } from '@/modules/wallet/types';
import type { Hash, ViemWalletClient } from '@/modules/wallet/viem-client';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useTransactionManager } from '@/modules/wallet/use-transaction-manager';

type Receipt = Awaited<ReturnType<ViemWalletClient['waitForTransactionReceipt']>>;

const HASH: Hash = '0xhash';

const getAssetMappingHandler = vi.fn(async () => ({ assets: { 'eip155:1/erc20:0xtoken': { symbol: 'TOKEN' } } }));
const updateStatePostTransaction = vi.fn(async () => {});

vi.mock('@/modules/assets/use-asset-info-cache', () => ({
  useAssetInfoCache: vi.fn(() => ({ getAssetMappingHandler })),
}));

vi.mock('@/modules/wallet/use-wallet-helper', () => ({
  useWalletHelper: vi.fn(() => ({ updateStatePostTransaction })),
}));

function txParams(overrides: Partial<TransactionParams> = {}): TransactionParams {
  return { amount: '1', chain: 'monad', native: true, to: '0xto', ...overrides };
}

function walletClient(): ViemWalletClient {
  return createMock<ViemWalletClient>({
    waitForTransactionReceipt: vi.fn(async () => createMock<Receipt>()),
  });
}

describe('useTransactionManager', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('handleTransactionSuccess', () => {
    it('should record the chain the transfer was prepared for', async () => {
      const { handleTransactionSuccess, recentTransactions } = useTransactionManager();

      await handleTransactionSuccess(walletClient(), HASH, txParams(), '0xfrom');
      await vi.waitFor(() => expect(get(recentTransactions)).toHaveLength(1));

      expect(get(recentTransactions)[0].chain).toBe('monad');
    });

    it('should mark the transaction completed once the receipt lands', async () => {
      const { handleTransactionSuccess, recentTransactions } = useTransactionManager();

      await handleTransactionSuccess(walletClient(), HASH, txParams(), '0xfrom');
      await vi.waitFor(() => expect(get(recentTransactions)[0]?.status).toBe('completed'));

      expect(updateStatePostTransaction).toHaveBeenCalledWith(
        expect.objectContaining({ chain: 'monad', hash: HASH }),
      );
    });

    it('should wait for the receipt of the hash it was given', async () => {
      const client = walletClient();
      const { handleTransactionSuccess } = useTransactionManager();

      await handleTransactionSuccess(client, HASH, txParams(), '0xfrom');

      expect(client.waitForTransactionReceipt).toHaveBeenCalledWith({ hash: HASH });
    });
  });

  describe('addRecentTransaction', () => {
    it('should resolve a token symbol for a non-native transfer', async () => {
      const { addRecentTransaction, recentTransactions } = useTransactionManager();

      await addRecentTransaction(HASH, 'eth', txParams({ assetIdentifier: 'eip155:1/erc20:0xtoken', native: false }), '0xfrom');

      expect(get(recentTransactions)[0].context).toContain('TOKEN');
    });

    it('should put the newest transaction first', async () => {
      const { addRecentTransaction, recentTransactions } = useTransactionManager();

      await addRecentTransaction('0xolder', 'eth', txParams(), '0xfrom');
      await addRecentTransaction('0xnewer', 'eth', txParams(), '0xfrom');

      expect(get(recentTransactions).map(tx => tx.hash)).toEqual(['0xnewer', '0xolder']);
    });
  });

  describe('reset', () => {
    it('should drop every recorded transaction', async () => {
      const { addRecentTransaction, recentTransactions, reset } = useTransactionManager();
      await addRecentTransaction(HASH, 'eth', txParams(), '0xfrom');

      reset();

      expect(get(recentTransactions)).toEqual([]);
    });
  });
});
