import { runSpecWith } from '@test/utils/mocks/native-task';
import { err, ok, type Result } from 'plainfp/result';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type AccountPayload, type XpubAccountPayload, XpubKeyType } from '@/modules/accounts/blockchain-accounts';
import { Cancelled, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import '@test/i18n';

const mocks = vi.hoisted(() => ({
  addBlockchainAccount: vi.fn(),
  addEvmAccount: vi.fn(),
  editAgnosticBlockchainAccount: vi.fn(),
  editBlockchainAccount: vi.fn(),
  editBtcAccount: vi.fn(),
  fetchEthStakingValidators: vi.fn(),
  getNativeAsset: vi.fn((chain: string): string => chain.toUpperCase()),
  notifyError: vi.fn(),
  queryAccounts: vi.fn(),
  queryBtcAccounts: vi.fn(),
  removeAgnosticBlockchainAccount: vi.fn(),
  removeBlockchainAccount: vi.fn(),
  resetAddressNamesData: vi.fn(),
  updateAccounts: vi.fn(),
  deleteXpub: vi.fn(),
}));

vi.mock('@/modules/accounts/api/use-blockchain-accounts-api', () => ({
  useBlockchainAccountsApi: vi.fn(() => ({
    addBlockchainAccount: mocks.addBlockchainAccount,
    addEvmAccount: mocks.addEvmAccount,
    deleteXpub: mocks.deleteXpub,
    editAgnosticBlockchainAccount: mocks.editAgnosticBlockchainAccount,
    editBlockchainAccount: mocks.editBlockchainAccount,
    editBtcAccount: mocks.editBtcAccount,
    queryAccounts: mocks.queryAccounts,
    queryBtcAccounts: mocks.queryBtcAccounts,
    removeAgnosticBlockchainAccount: mocks.removeAgnosticBlockchainAccount,
    removeBlockchainAccount: mocks.removeBlockchainAccount,
  })),
}));

vi.mock('@/modules/accounts/use-eth-staking', () => ({
  useEthStaking: vi.fn(() => ({ fetchEthStakingValidators: mocks.fetchEthStakingValidators })),
}));

vi.mock('@/modules/accounts/use-blockchain-accounts-store', () => ({
  useBlockchainAccountsStore: vi.fn(() => ({ updateAccounts: mocks.updateAccounts })),
}));

vi.mock('@/modules/accounts/address-book/use-address-name-resolution', () => ({
  useAddressNameResolution: vi.fn(() => ({ resetAddressNamesData: mocks.resetAddressNamesData })),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({
    getChainName: (chain: string): string => chain,
    getNativeAsset: mocks.getNativeAsset,
  })),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  getErrorMessage: (e: unknown): string => (e instanceof Error ? e.message : String(e)),
  useNotifications: vi.fn(() => ({ notifyError: mocks.notifyError })),
}));

const runTaskResult = vi.fn();
const submitTask = vi.fn(runSpecWith(runTaskResult));

vi.mock('@/modules/task-center/use-native-task', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useNativeTask: vi.fn(() => ({ cancelByType: vi.fn(() => vi.fn()), runTaskResult, statusOf: vi.fn(), submitTask })),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn() },
}));

// runTaskResult is mocked and does not invoke its api callback; opt into invoking it when the API call must run.
function whenOk<R>(value: R, invoke = true): void {
  runTaskResult.mockImplementation(async (task: () => Promise<unknown>): Promise<Result<R, TaskError>> => {
    if (invoke)
      await task();
    return ok(value);
  });
}

function whenActionable(message: string): void {
  runTaskResult.mockResolvedValue(err(TaskFailed({ message })));
}

function whenCancelled(): void {
  runTaskResult.mockResolvedValue(err(Cancelled({ message: 'cancelled' })));
}

async function importModule(): Promise<typeof import('./use-blockchain-accounts')> {
  return import('./use-blockchain-accounts');
}

describe('useBlockchainAccounts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('addAccount', () => {
    const payload: AccountPayload[] = [{ address: '0xabc', tags: null }];

    it('should return the first result address on success', async () => {
      whenOk<string[] | true>(['0xdef']);
      const { useBlockchainAccounts } = await importModule();
      const result = await useBlockchainAccounts().addAccount('eth', payload);
      expect(mocks.addBlockchainAccount).toHaveBeenCalledWith('eth', payload);
      expect(result).toBe('0xdef');
    });

    it('should return the joined addresses when the result is true', async () => {
      whenOk<string[] | true>(true);
      const { useBlockchainAccounts } = await importModule();
      const result = await useBlockchainAccounts().addAccount('eth', [
        { address: '0xabc', tags: null },
        { address: '0xdef', tags: null },
      ]);
      expect(result).toBe('0xabc,\n0xdef');
    });

    it('should return an empty string when the result array is empty', async () => {
      whenOk<string[] | true>([]);
      const { useBlockchainAccounts } = await importModule();
      expect(await useBlockchainAccounts().addAccount('eth', payload)).toBe('');
    });

    it('should use the xpub as the address for an xpub payload', async () => {
      whenOk<string[] | true>(['0xdef']);
      const xpubPayload: XpubAccountPayload = {
        tags: null,
        xpub: { derivationPath: '', xpub: 'xpub123', xpubType: XpubKeyType.XPUB },
      };
      const { useBlockchainAccounts } = await importModule();
      await useBlockchainAccounts().addAccount('btc', xpubPayload);
      expect(mocks.addBlockchainAccount).toHaveBeenCalledWith('btc', xpubPayload);
    });

    it('should throw on an actionable failure', async () => {
      whenActionable('boom');
      const { useBlockchainAccounts } = await importModule();
      await expect(useBlockchainAccounts().addAccount('eth', payload)).rejects.toThrow('boom');
    });

    it('should return an empty string on a cancelled task', async () => {
      whenCancelled();
      const { useBlockchainAccounts } = await importModule();
      expect(await useBlockchainAccounts().addAccount('eth', payload)).toBe('');
    });
  });

  describe('addEvmAccount', () => {
    const payload: AccountPayload = { address: '0xabc', tags: null };

    it('should return the result on success', async () => {
      whenOk({ added: { eth: ['0xabc'] } });
      const { useBlockchainAccounts } = await importModule();
      const result = await useBlockchainAccounts().addEvmAccount(payload);
      expect(mocks.addEvmAccount).toHaveBeenCalledWith(payload);
      expect(result).toStrictEqual({ added: { eth: ['0xabc'] } });
    });

    it('should throw on an actionable failure', async () => {
      whenActionable('nope');
      const { useBlockchainAccounts } = await importModule();
      await expect(useBlockchainAccounts().addEvmAccount(payload)).rejects.toThrow('nope');
    });

    it('should return an empty object on a cancelled task', async () => {
      whenCancelled();
      const { useBlockchainAccounts } = await importModule();
      expect(await useBlockchainAccounts().addEvmAccount(payload)).toStrictEqual({});
    });
  });

  describe('editAccount', () => {
    it('should edit a btc account and reset address names for a non-xpub payload', async () => {
      mocks.editBtcAccount.mockResolvedValue({ standalone: [], xpubs: [] });
      const { useBlockchainAccounts } = await importModule();
      const result = await useBlockchainAccounts().editAccount({ address: 'bc1', tags: null }, 'btc');
      expect(mocks.editBtcAccount).toHaveBeenCalled();
      expect(result).toStrictEqual([]);
      expect(mocks.resetAddressNamesData).toHaveBeenCalledOnce();
    });

    it('should not reset address names for an xpub payload', async () => {
      mocks.editBtcAccount.mockResolvedValue({ standalone: [], xpubs: [] });
      const xpubPayload: XpubAccountPayload = {
        tags: null,
        xpub: { derivationPath: '', xpub: 'xpub123', xpubType: XpubKeyType.XPUB },
      };
      const { useBlockchainAccounts } = await importModule();
      await useBlockchainAccounts().editAccount(xpubPayload, 'btc');
      expect(mocks.resetAddressNamesData).not.toHaveBeenCalled();
    });

    it('should edit an evm account and map the result into accounts', async () => {
      mocks.editBlockchainAccount.mockResolvedValue([{ address: '0xabc', label: null, tags: null }]);
      const { useBlockchainAccounts } = await importModule();
      const result = await useBlockchainAccounts().editAccount({ address: '0xabc', tags: null }, 'eth');
      expect(result).toHaveLength(1);
      expect(result[0]).toMatchObject({ chain: 'eth', data: { address: '0xabc', type: 'address' }, nativeAsset: 'ETH' });
      expect(mocks.resetAddressNamesData).toHaveBeenCalledOnce();
    });
  });

  describe('editAgnosticAccount', () => {
    it('should edit the account and reset address names', async () => {
      mocks.editAgnosticBlockchainAccount.mockResolvedValue(true);
      const { useBlockchainAccounts } = await importModule();
      const result = await useBlockchainAccounts().editAgnosticAccount('evm', { address: '0xabc', tags: null });
      expect(result).toBe(true);
      expect(mocks.resetAddressNamesData).toHaveBeenCalledOnce();
    });
  });

  describe('removeAccount', () => {
    it('should not notify on success', async () => {
      whenOk({ perAccount: {}, totals: { assets: {}, liabilities: {} } }, false);
      const { useBlockchainAccounts } = await importModule();
      await useBlockchainAccounts().removeAccount({ accounts: ['0xabc'], chain: 'eth' });
      expect(mocks.notifyError).not.toHaveBeenCalled();
    });

    it('should notify on an actionable failure', async () => {
      whenActionable('remove failed');
      const { useBlockchainAccounts } = await importModule();
      await useBlockchainAccounts().removeAccount({ accounts: ['0xabc'], chain: 'eth' });
      expect(mocks.notifyError).toHaveBeenCalledOnce();
    });
  });

  describe('removeAgnosticAccount', () => {
    it('should notify on an actionable failure', async () => {
      whenActionable('agnostic failed');
      const { useBlockchainAccounts } = await importModule();
      await useBlockchainAccounts().removeAgnosticAccount('evm', '0xabc');
      expect(mocks.notifyError).toHaveBeenCalledOnce();
    });
  });

  describe('deleteXpub', () => {
    it('should notify on an actionable failure', async () => {
      whenActionable('xpub failed');
      const { useBlockchainAccounts } = await importModule();
      await useBlockchainAccounts().deleteXpub({ chain: 'btc', xpub: 'xpub123' });
      expect(mocks.notifyError).toHaveBeenCalledOnce();
    });

    it('should not notify on success', async () => {
      whenOk(true, false);
      const { useBlockchainAccounts } = await importModule();
      await useBlockchainAccounts().deleteXpub({ chain: 'btc', xpub: 'xpub123' });
      expect(mocks.notifyError).not.toHaveBeenCalled();
    });
  });

  describe('fetch', () => {
    it('should fetch btc accounts for a btc chain', async () => {
      mocks.queryBtcAccounts.mockResolvedValue({ standalone: [], xpubs: [] });
      const { useBlockchainAccounts } = await importModule();
      await useBlockchainAccounts().fetch('btc');
      expect(mocks.queryBtcAccounts).toHaveBeenCalledWith('btc');
      expect(mocks.updateAccounts).toHaveBeenCalledWith('btc', []);
    });

    it('should fetch eth staking validators for eth2', async () => {
      const { useBlockchainAccounts } = await importModule();
      await useBlockchainAccounts().fetch('eth2');
      expect(mocks.fetchEthStakingValidators).toHaveBeenCalledOnce();
    });

    it('should fetch blockchain accounts for a regular chain', async () => {
      mocks.queryAccounts.mockResolvedValue([{ address: '0xabc', label: null, tags: null }]);
      const { useBlockchainAccounts } = await importModule();
      await useBlockchainAccounts().fetch('eth');
      expect(mocks.queryAccounts).toHaveBeenCalledWith('eth');
      expect(mocks.updateAccounts).toHaveBeenCalledOnce();
    });

    it('should notify when fetching blockchain accounts fails', async () => {
      mocks.queryAccounts.mockRejectedValue(new Error('query failed'));
      const { useBlockchainAccounts } = await importModule();
      await useBlockchainAccounts().fetch('eth');
      expect(mocks.notifyError).toHaveBeenCalledOnce();
    });

    it('should notify when fetching btc accounts fails', async () => {
      mocks.queryBtcAccounts.mockRejectedValue(new Error('btc failed'));
      const { useBlockchainAccounts } = await importModule();
      await useBlockchainAccounts().fetch('bch');
      expect(mocks.notifyError).toHaveBeenCalledOnce();
    });
  });
});
