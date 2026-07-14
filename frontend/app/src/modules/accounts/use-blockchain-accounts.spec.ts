import type { TaskResult } from '@/modules/core/tasks/use-task-handler';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type AccountPayload, type XpubAccountPayload, XpubKeyType } from '@/modules/accounts/blockchain-accounts';
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
  runTask: vi.fn(),
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

vi.mock('@/modules/core/tasks/use-task-handler', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/modules/core/tasks/use-task-handler')>();
  return {
    ...actual,
    useTaskHandler: vi.fn(() => ({ runTask: mocks.runTask })),
  };
});

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn() },
}));

function success<R>(result: R): TaskResult<R> {
  return { result, success: true };
}

function actionable(message: string): TaskResult<never> {
  return { backendCancelled: false, cancelled: false, error: new Error(message), message, skipped: false, success: false };
}

function cancelled(): TaskResult<never> {
  return { backendCancelled: false, cancelled: true, message: 'cancelled', skipped: false, success: false };
}

// runTask is mocked and does not invoke its callback; opt into invoking it when the API call must run.
function whenTask<R>(outcome: TaskResult<R>, invoke = true): void {
  mocks.runTask.mockImplementation(async (task: () => Promise<unknown>): Promise<TaskResult<R>> => {
    if (invoke)
      await task();
    return outcome;
  });
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
      whenTask(success(['0xdef']));
      const { useBlockchainAccounts } = await importModule();
      const result = await useBlockchainAccounts().addAccount('eth', payload);
      expect(mocks.addBlockchainAccount).toHaveBeenCalledWith('eth', payload);
      expect(result).toBe('0xdef');
    });

    it('should return the joined addresses when the result is true', async () => {
      whenTask(success<string[] | true>(true));
      const { useBlockchainAccounts } = await importModule();
      const result = await useBlockchainAccounts().addAccount('eth', [
        { address: '0xabc', tags: null },
        { address: '0xdef', tags: null },
      ]);
      expect(result).toBe('0xabc,\n0xdef');
    });

    it('should return an empty string when the result array is empty', async () => {
      whenTask(success<string[]>([]));
      const { useBlockchainAccounts } = await importModule();
      expect(await useBlockchainAccounts().addAccount('eth', payload)).toBe('');
    });

    it('should use the xpub as the address for an xpub payload', async () => {
      whenTask(success(['0xdef']));
      const xpubPayload: XpubAccountPayload = {
        tags: null,
        xpub: { derivationPath: '', xpub: 'xpub123', xpubType: XpubKeyType.XPUB },
      };
      const { useBlockchainAccounts } = await importModule();
      await useBlockchainAccounts().addAccount('btc', xpubPayload);
      expect(mocks.addBlockchainAccount).toHaveBeenCalledWith('btc', xpubPayload);
    });

    it('should throw on an actionable failure', async () => {
      whenTask(actionable('boom'), false);
      const { useBlockchainAccounts } = await importModule();
      await expect(useBlockchainAccounts().addAccount('eth', payload)).rejects.toThrow('boom');
    });

    it('should return an empty string on a cancelled task', async () => {
      whenTask(cancelled(), false);
      const { useBlockchainAccounts } = await importModule();
      expect(await useBlockchainAccounts().addAccount('eth', payload)).toBe('');
    });
  });

  describe('addEvmAccount', () => {
    const payload: AccountPayload = { address: '0xabc', tags: null };

    it('should return the result on success', async () => {
      whenTask(success({ added: { eth: ['0xabc'] } }));
      const { useBlockchainAccounts } = await importModule();
      const result = await useBlockchainAccounts().addEvmAccount(payload);
      expect(mocks.addEvmAccount).toHaveBeenCalledWith(payload);
      expect(result).toStrictEqual({ added: { eth: ['0xabc'] } });
    });

    it('should throw on an actionable failure', async () => {
      whenTask(actionable('nope'), false);
      const { useBlockchainAccounts } = await importModule();
      await expect(useBlockchainAccounts().addEvmAccount(payload)).rejects.toThrow('nope');
    });

    it('should return an empty object on a cancelled task', async () => {
      whenTask(cancelled(), false);
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
      whenTask(success({ perAccount: {}, totals: { assets: {}, liabilities: {} } }), false);
      const { useBlockchainAccounts } = await importModule();
      await useBlockchainAccounts().removeAccount({ accounts: ['0xabc'], chain: 'eth' });
      expect(mocks.notifyError).not.toHaveBeenCalled();
    });

    it('should notify on an actionable failure', async () => {
      whenTask(actionable('remove failed'), false);
      const { useBlockchainAccounts } = await importModule();
      await useBlockchainAccounts().removeAccount({ accounts: ['0xabc'], chain: 'eth' });
      expect(mocks.notifyError).toHaveBeenCalledOnce();
    });
  });

  describe('removeAgnosticAccount', () => {
    it('should notify on an actionable failure', async () => {
      whenTask(actionable('agnostic failed'), false);
      const { useBlockchainAccounts } = await importModule();
      await useBlockchainAccounts().removeAgnosticAccount('evm', '0xabc');
      expect(mocks.notifyError).toHaveBeenCalledOnce();
    });
  });

  describe('deleteXpub', () => {
    it('should notify on an actionable failure', async () => {
      whenTask(actionable('xpub failed'), false);
      const { useBlockchainAccounts } = await importModule();
      await useBlockchainAccounts().deleteXpub({ chain: 'btc', xpub: 'xpub123' });
      expect(mocks.notifyError).toHaveBeenCalledOnce();
    });

    it('should not notify on success', async () => {
      whenTask(success(true), false);
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
