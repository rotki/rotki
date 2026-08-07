import { Blockchain } from '@rotki/common';
import { err, isErr, ok } from 'plainfp/result';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { EVM_PSEUDO_CHAIN } from '@/modules/accounts/accounts.activity';
import { type XpubAccountPayload, XpubKeyType } from '@/modules/accounts/blockchain-accounts';
import { Module } from '@/modules/core/common/modules';
import { Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
import '@test/i18n';

const h = vi.hoisted(() => ({
  addAccount: vi.fn(),
  addEvmAccount: vi.fn(),
  createFailureNotification: vi.fn(),
  detectTokens: vi.fn(),
  enableModule: vi.fn(),
  fetchTags: vi.fn(),
  getAddresses: vi.fn((): string[] => []),
  notifyFailedToAddAddress: vi.fn(),
  notifyUser: vi.fn(),
  supportsTransactions: vi.fn((): boolean => true),
  trackAddedAddresses: vi.fn(),
}));

vi.mock('@/modules/accounts/use-account-additions', () => ({
  useAccountAdditions: vi.fn(() => ({ addAccount: h.addAccount, addEvmAccount: h.addEvmAccount })),
}));

// A faithful stand-in: every item runs, each gets a parent. The real one submits an activity, which
// would drag the whole task layer (and pinia) into these specs; its own behaviour is covered in
// use-activity-batch.spec.ts.
async function runEach<TItem, TResult>(items: readonly TItem[], run: (item: TItem, parent: string) => Promise<TResult>): Promise<TResult[]> {
  return Promise.all(items.map(async item => run(item, 'accounts:add:batch')));
}

vi.mock('@/modules/accounts/use-account-addition-batch', () => ({
  // Not mocked: it is a pure comparison against the pseudo-chain, and stubbing it would let the
  // spec disagree with the module about what "every EVM chain" means.
  isEveryEvmChain: (chain: string): boolean => chain === 'EVM',
  useAccountAdditionBatch: vi.fn(() => ({
    runAdditionBatch: async <TItem, TResult>(
      _chain: string,
      items: readonly TItem[],
      _addressOf: (item: TItem) => string,
      run: (item: TItem, parent: string) => Promise<TResult>,
    ): Promise<TResult[]> => runEach(items, run),
    runEvmAdditionBatch: async <TItem, TResult>(
      items: readonly TItem[],
      _addressOf: (item: TItem) => string,
      run: (item: TItem, parent: string) => Promise<TResult>,
    ): Promise<TResult[]> => runEach(items, run),
  })),
}));

vi.mock('@/modules/balances/blockchain/use-token-detection-orchestrator', () => ({
  useTokenDetectionOrchestrator: vi.fn(() => ({ detectTokens: h.detectTokens })),
}));

vi.mock('@/modules/accounts/use-blockchain-accounts-store', () => ({
  useBlockchainAccountsStore: vi.fn(() => ({ trackAddedAddresses: h.trackAddedAddresses })),
}));

vi.mock('@/modules/tags/use-tag-operations', () => ({
  useTagOperations: vi.fn(() => ({ fetchTags: h.fetchTags })),
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: vi.fn(() => ({ enableModule: h.enableModule })),
}));

vi.mock('@/modules/balances/blockchain/use-account-addresses', () => ({
  useAccountAddresses: vi.fn(() => ({ getAddresses: h.getAddresses })),
}));

vi.mock('@/modules/accounts/use-account-addition-notifications', () => ({
  useAccountAdditionNotifications: vi.fn(() => ({
    createFailureNotification: h.createFailureNotification,
    notifyFailedToAddAddress: h.notifyFailedToAddAddress,
    notifyUser: h.notifyUser,
  })),
}));

vi.mock('@/modules/core/common/use-supported-chains', async () => {
  const { ref } = await import('vue');
  return {
    useSupportedChains: vi.fn(() => ({
      evmChains: ref(['eth', 'optimism']),
      supportsTransactions: h.supportsTransactions,
    })),
  };
});

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn() },
}));

async function importModule(): Promise<typeof import('./use-account-addition-service')> {
  return import('./use-account-addition-service');
}

describe('useAccountAdditionService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    h.getAddresses.mockReturnValue([]);
    h.supportsTransactions.mockReturnValue(true);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('getNewAccountPayload', () => {
    it('should filter out already known addresses case-insensitively', async () => {
      h.getAddresses.mockReturnValue(['0xabc']);
      const { useAccountAdditionService } = await importModule();
      const result = useAccountAdditionService().getNewAccountPayload('eth', [
        { address: '0xABC', tags: null },
        { address: '0xdef', tags: null },
      ]);
      expect(result).toEqual([{ address: '0xdef', tags: null }]);
    });
  });

  describe('addSingleAccount', () => {
    it('should return the address on success', async () => {
      h.addAccount.mockResolvedValue(ok('0xabc'));
      const { useAccountAdditionService } = await importModule();
      const result = await useAccountAdditionService().addSingleAccount({ address: '0xabc', tags: null }, 'eth');
      // The third argument is the batch options; a single add has no umbrella to parent it to.
      expect(h.addAccount).toHaveBeenCalledWith('eth', [{ address: '0xabc', tags: null }], undefined);
      expect(result).toStrictEqual(ok('0xabc'));
    });

    it('should pass an xpub payload through directly', async () => {
      h.addAccount.mockResolvedValue(ok('xpub123'));
      const xpubPayload: XpubAccountPayload = {
        tags: null,
        xpub: { derivationPath: '', xpub: 'xpub123', xpubType: XpubKeyType.XPUB },
      };
      const { useAccountAdditionService } = await importModule();
      const result = await useAccountAdditionService().addSingleAccount(xpubPayload, 'btc');
      expect(h.addAccount).toHaveBeenCalledWith('btc', xpubPayload, undefined);
      expect(result).toStrictEqual(ok('xpub123'));
    });

    it('should return an error result when the addition throws', async () => {
      h.addAccount.mockResolvedValue(err(TaskFailed({ message: 'nope' })));
      const { useAccountAdditionService } = await importModule();
      const result = await useAccountAdditionService().addSingleAccount({ address: '0xabc', tags: null }, 'eth');
      expect(isErr(result)).toBe(true);
    });
  });

  describe('addSingleEvmAddress', () => {
    // `added` is an optional record, so `{}` is a valid response: truthy, but with nothing to
    // destructure. That threw `undefined is not iterable` out of the composable — surfacing as a
    // raw type error in the add dialog, and in a bulk add being swallowed by the queue so the
    // address landed in neither the added nor the failed list.
    it('should handle an empty added record without throwing', async () => {
      h.addEvmAccount.mockResolvedValue(ok({ added: {} }));
      const { useAccountAdditionService } = await importModule();
      const result = await useAccountAdditionService().addSingleEvmAddress({ address: '0xabc', tags: null });
      assert(!isErr(result));
      expect(result.value).toStrictEqual([]);
      expect(h.notifyUser).not.toHaveBeenCalled();
    });

    it('should expand added chains and notify the user', async () => {
      h.addEvmAccount.mockResolvedValue(ok({ added: { '0xabc': ['eth', 'optimism'] } }));
      const { useAccountAdditionService } = await importModule();
      const result = await useAccountAdditionService().addSingleEvmAddress({ address: '0xabc', tags: null });
      assert(!isErr(result));
      expect(result.value).toEqual([
        { address: '0xabc', chain: 'eth' },
        { address: '0xabc', chain: 'optimism' },
      ]);
      expect(h.notifyUser).toHaveBeenCalledOnce();
      expect(h.createFailureNotification).toHaveBeenCalledOnce();
    });

    it('should expand to all evm chains when the result is "all"', async () => {
      h.addEvmAccount.mockResolvedValue(ok({ added: { '0xabc': ['all'] } }));
      const { useAccountAdditionService } = await importModule();
      const result = await useAccountAdditionService().addSingleEvmAddress({ address: '0xabc', tags: null });
      assert(!isErr(result));
      expect(result.value.map(account => account.chain)).toEqual(['eth', 'optimism']);
    });

    it('should skip chains that are not valid blockchains', async () => {
      h.addEvmAccount.mockResolvedValue(ok({ added: { '0xabc': ['eth', 'not-a-chain'] } }));
      const { useAccountAdditionService } = await importModule();
      const result = await useAccountAdditionService().addSingleEvmAddress({ address: '0xabc', tags: null });
      assert(!isErr(result));
      expect(result.value.map(account => account.chain)).toEqual(['eth']);
    });

    it('should return an error result when the addition throws', async () => {
      h.addEvmAccount.mockResolvedValue(err(TaskFailed({ message: 'boom' })));
      const { useAccountAdditionService } = await importModule();
      const result = await useAccountAdditionService().addSingleEvmAddress({ address: '0xabc', tags: null });
      expect(isErr(result)).toBe(true);
    });
  });

  describe('addAccounts', () => {
    const onComplete = vi.fn<() => Promise<void>>(async () => {});

    it('should collect added accounts and invoke the completion callback', async () => {
      h.addAccount.mockResolvedValue(ok('0xabc'));
      const { useAccountAdditionService } = await importModule();
      const summary = await useAccountAdditionService().addAccounts('eth', [{ address: '0xabc', tags: null }], undefined, onComplete);

      expect(summary.added).toStrictEqual([{ address: '0xabc', chain: 'eth' }]);
      expect(onComplete).toHaveBeenCalledWith({ addedAccounts: [{ address: '0xabc', chain: 'eth' }], chain: 'eth', isXpub: false, modulesToEnable: undefined });
      expect(h.notifyFailedToAddAddress).not.toHaveBeenCalled();
    });

    // The reason travels with the payload: a form caller reads the cause off it to fill in
    // per-field errors, which a payload-only summary cannot support.
    it('should notify about failed additions and report them with their reason', async () => {
      const cause = new Error('{"address": ["invalid"]}');
      h.addAccount.mockResolvedValue(err(TaskFailed({ cause, message: 'nope' })));
      const { useAccountAdditionService } = await importModule();
      const summary = await useAccountAdditionService().addAccounts('eth', [{ address: '0xabc', tags: null }], undefined, onComplete);

      expect(summary.failed).toStrictEqual([{
        account: { address: '0xabc', tags: null },
        error: TaskFailed({ cause, message: 'nope' }),
      }]);
      expect(h.notifyFailedToAddAddress).toHaveBeenCalledOnce();
    });

    // A cancellation is neither added nor failed: reporting it would raise "failed to add" for work
    // the user deliberately stopped.
    it('should record a cancellation without reporting it as a failure', async () => {
      h.addAccount.mockResolvedValue(err(Cancelled({ message: 'cancelled' })));
      const { useAccountAdditionService } = await importModule();
      const summary = await useAccountAdditionService().addAccounts('eth', [{ address: '0xabc', tags: null }], undefined, onComplete);

      expect(summary).toMatchObject({ added: [], cancelled: true, failed: [] });
      expect(h.notifyFailedToAddAddress).not.toHaveBeenCalled();
    });

    it('should route the pseudo-chain through the evm addition', async () => {
      h.addEvmAccount.mockResolvedValue(ok({ added: { '0xabc': ['eth'] } }));
      const { useAccountAdditionService } = await importModule();
      const summary = await useAccountAdditionService().addAccounts(EVM_PSEUDO_CHAIN, [{ address: '0xabc', tags: null }], undefined, onComplete);

      expect(h.addEvmAccount).toHaveBeenCalledOnce();
      expect(summary.added).toStrictEqual([{ address: '0xabc', chain: 'eth' }]);
      // No `chain` on the completion params: the pseudo-chain is not one to refresh.
      expect(onComplete).toHaveBeenCalledWith({ addedAccounts: [{ address: '0xabc', chain: 'eth' }], chain: undefined, isXpub: false, modulesToEnable: undefined });
    });

    // An xpub is one unit of work, so it never fans out — but it returns the same summary, which is
    // what lets the caller have a single shape to handle.
    it('should add an xpub through the same function and summary', async () => {
      h.addAccount.mockResolvedValue(ok('xpub123'));
      const xpubPayload: XpubAccountPayload = {
        tags: null,
        xpub: { derivationPath: '', xpub: 'xpub123', xpubType: XpubKeyType.XPUB },
      };
      const { useAccountAdditionService } = await importModule();
      const summary = await useAccountAdditionService().addAccounts('btc', xpubPayload, undefined, onComplete);

      expect(summary.added).toStrictEqual([{ address: 'xpub123', chain: 'btc' }]);
      expect(onComplete).toHaveBeenCalledWith(expect.objectContaining({ isXpub: true }));
    });

    // The notification lists addresses, so an xpub has no row in it — but the summary must still
    // carry the failure or the form would close as though the xpub had been added.
    it('should report a failed xpub in the summary but not in the notification', async () => {
      h.addAccount.mockResolvedValue(err(TaskFailed({ message: 'nope' })));
      const xpubPayload: XpubAccountPayload = {
        tags: null,
        xpub: { derivationPath: '', xpub: 'xpub123', xpubType: XpubKeyType.XPUB },
      };
      const { useAccountAdditionService } = await importModule();
      const summary = await useAccountAdditionService().addAccounts('btc', xpubPayload, undefined, onComplete);

      expect(summary.failed).toStrictEqual([{
        account: xpubPayload,
        error: TaskFailed({ message: 'nope' }),
      }]);
      expect(h.notifyFailedToAddAddress).not.toHaveBeenCalled();
    });
  });

  describe('completeAccountAddition', () => {
    const added = [{ address: '0xabc', chain: Blockchain.ETH }];

    it('should fetch account metadata for transaction-supporting chains', async () => {
      const onRefreshAccounts = vi.fn<() => Promise<void>>(async () => {});
      const onFetchAccounts = vi.fn<() => Promise<void>>(async () => {});
      const { useAccountAdditionService } = await importModule();
      await useAccountAdditionService().completeAccountAddition(
        { addedAccounts: added, chain: 'eth' },
        onRefreshAccounts,
        onFetchAccounts,
      );
      expect(h.fetchTags).toHaveBeenCalledOnce();
      expect(h.trackAddedAddresses).toHaveBeenCalledWith(['0xabc']);
      expect(onFetchAccounts).toHaveBeenCalledWith('eth', true);
      expect(onRefreshAccounts).not.toHaveBeenCalled();
      expect(h.detectTokens).toHaveBeenCalledWith('eth', ['0xabc']);
    });

    it('should refresh accounts when the chain does not support transactions', async () => {
      h.supportsTransactions.mockReturnValue(false);
      const onRefreshAccounts = vi.fn<() => Promise<void>>(async () => {});
      const onFetchAccounts = vi.fn<() => Promise<void>>(async () => {});
      const { useAccountAdditionService } = await importModule();
      await useAccountAdditionService().completeAccountAddition(
        { addedAccounts: added, chain: 'btc', isXpub: true },
        onRefreshAccounts,
        onFetchAccounts,
      );
      expect(onRefreshAccounts).toHaveBeenCalledWith({ addresses: ['0xabc'], blockchain: 'btc', isXpub: true });
      expect(onFetchAccounts).not.toHaveBeenCalled();
      expect(h.detectTokens).not.toHaveBeenCalled();
    });

    it('should enable the requested modules for eth accounts', async () => {
      const onRefreshAccounts = vi.fn<() => Promise<void>>(async () => {});
      const onFetchAccounts = vi.fn<() => Promise<void>>(async () => {});
      const { useAccountAdditionService } = await importModule();
      await useAccountAdditionService().completeAccountAddition(
        { addedAccounts: added, chain: 'eth', modulesToEnable: [Module.ETH2] },
        onRefreshAccounts,
        onFetchAccounts,
      );
      expect(h.enableModule).toHaveBeenCalledWith({ addresses: ['0xabc'], enable: [Module.ETH2] });
    });
  });
});
