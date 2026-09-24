import { runSpecWith } from '@test/utils/mocks/native-task';
import { err, isErr, ok, type Result } from 'plainfp/result';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { accountAddActivity, accountImportActivity, EVM_PSEUDO_CHAIN } from '@/modules/accounts/accounts.activity';
import { type AccountPayload, type XpubAccountPayload, XpubKeyType } from '@/modules/accounts/blockchain-accounts';
import { Cancelled, Skipped, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { peekActivityDetail } from '@/modules/task-center/use-activity-detail';
import '@test/i18n';

const mocks = vi.hoisted(() => ({
  addBlockchainAccount: vi.fn(),
  addEvmAccount: vi.fn(),
}));

vi.mock('@/modules/accounts/api/use-blockchain-accounts-api', () => ({
  useBlockchainAccountsApi: vi.fn(() => ({
    addBlockchainAccount: mocks.addBlockchainAccount,
    addEvmAccount: mocks.addEvmAccount,
  })),
}));

const runTaskResult = vi.fn();
const submitTask = vi.fn(runSpecWith(runTaskResult));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({ getChainName: (chain: string): string => `name:${chain}` })),
}));

vi.mock('@/modules/task-center/use-native-task', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useNativeTask: vi.fn(() => ({ cancelByType: vi.fn(() => vi.fn()), runTaskResult, statusOf: vi.fn(), submitTask })),
}));

/**
 * Stubs the task runner so the next addition succeeds with `value`.
 *
 * @param value - the payload the runner resolves with
 * @param invoke - pass `false` to resolve without running the wrapped api callback at all
 */
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

async function importModule(): Promise<typeof import('./use-account-additions')> {
  return import('./use-account-additions');
}

describe('useAccountAdditions', () => {
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
      const { useAccountAdditions } = await importModule();
      const result = await useAccountAdditions().addAccount('eth', payload);
      expect(mocks.addBlockchainAccount).toHaveBeenCalledWith('eth', payload);
      expect(result).toStrictEqual(ok('0xdef'));
    });

    it('should return the joined addresses when the result is true', async () => {
      whenOk<string[] | true>(true);
      const { useAccountAdditions } = await importModule();
      const result = await useAccountAdditions().addAccount('eth', [
        { address: '0xabc', tags: null },
        { address: '0xdef', tags: null },
      ]);
      expect(result).toStrictEqual(ok('0xabc,\n0xdef'));
    });

    it('should return an error when the result array is empty', async () => {
      whenOk<string[] | true>([]);
      const { useAccountAdditions } = await importModule();
      expect(isErr(await useAccountAdditions().addAccount('eth', payload))).toBe(true);
    });

    it('should use the xpub as the address for an xpub payload', async () => {
      whenOk<string[] | true>(['0xdef']);
      const xpubPayload: XpubAccountPayload = {
        tags: null,
        xpub: { derivationPath: '', xpub: 'xpub123', xpubType: XpubKeyType.XPUB },
      };
      const { useAccountAdditions } = await importModule();
      await useAccountAdditions().addAccount('btc', xpubPayload);
      expect(mocks.addBlockchainAccount).toHaveBeenCalledWith('btc', xpubPayload);
    });

    it('should give each address its own activity id on the same chain, so neither dedups onto the other', async () => {
      whenOk<string[] | true>(true);
      const { useAccountAdditions } = await importModule();
      const accounts = useAccountAdditions();

      await accounts.addAccount('eth', [{ address: '0xabc', tags: null }]);
      await accounts.addAccount('eth', [{ address: '0xdef', tags: null }]);

      const [first, second] = submitTask.mock.calls.map(([spec]) => spec.id);
      expect(first).not.toBe(second);
    });

    it('should return the failure as a value on an actionable failure', async () => {
      whenActionable('boom');
      const { useAccountAdditions } = await importModule();
      expect(isErr(await useAccountAdditions().addAccount('eth', payload))).toBe(true);
    });

    it('should return an error, not an empty string, on a cancelled task', async () => {
      whenCancelled();
      const { useAccountAdditions } = await importModule();
      const result = await useAccountAdditions().addAccount('eth', payload);
      assert(isErr(result));
      expect(result).not.toStrictEqual(ok(''));
    });
  });

  describe('reportTracked', () => {
    it('should settle skipped as already tracked, under its parent, without calling the backend', async () => {
      const target = { address: '0xabc', kind: 'address' } as const;
      const parent = accountImportActivity.id({ source: 'csv' });
      const { useAccountAdditions } = await importModule();
      await useAccountAdditions().reportTracked('eth', target, { parent, userStarted: true });

      expect(submitTask).toHaveBeenCalledWith(expect.objectContaining({
        id: accountAddActivity.id({ chain: 'eth', target }),
        parent,
        userStarted: true,
      }));
      expect(await submitTask.mock.results[0]?.value).toStrictEqual(
        err(Skipped({ message: 'actions.balances.blockchain_accounts_add.skipped.tracked' })),
      );
      expect(runTaskResult).not.toHaveBeenCalled();
    });
  });

  describe('addEvmAccount', () => {
    const payload: AccountPayload = { address: '0xabc', tags: null };

    const subject = { chain: EVM_PSEUDO_CHAIN, target: { address: '0xabc', kind: 'address' } } as const;

    it('should return the result on success', async () => {
      whenOk({ added: { '0xabc': ['eth'] } });
      const { useAccountAdditions } = await importModule();
      const result = await useAccountAdditions().addEvmAccount(payload);
      expect(mocks.addEvmAccount).toHaveBeenCalledWith(payload);
      expect(result).toStrictEqual(ok({ added: { '0xabc': ['eth'] } }));
    });

    it('should publish where the address landed, per chain, once it was added', async () => {
      whenOk({ added: { '0xabc': ['eth', 'base'] }, existed: { '0xabc': ['optimism'] }, noActivity: { '0xabc': ['gnosis', 'scroll'] } });
      const { useAccountAdditions } = await importModule();
      await useAccountAdditions().addEvmAccount(payload);
      expect(peekActivityDetail(accountAddActivity, subject)).toStrictEqual({
        added: ['eth', 'base'],
        everyChain: false,
        existed: ['optimism'],
        failed: [],
        noActivity: ['gnosis', 'scroll'],
      });
    });

    it('should settle skipped asking for attention, naming no activity, when the address is active on no chain', async () => {
      whenOk({ noActivity: { '0xabc': ['all'] } });
      const { useAccountAdditions } = await importModule();
      const result = await useAccountAdditions().addEvmAccount(payload);
      expect(result).toStrictEqual(err(Skipped({ attention: true, message: 'actions.balances.blockchain_accounts_add.skipped.no_activity' })));
    });

    it('should settle skipped without asking for attention, naming it tracked, when every chain already has it', async () => {
      whenOk({ existed: { '0xabc': ['all'] } });
      const { useAccountAdditions } = await importModule();
      const result = await useAccountAdditions().addEvmAccount(payload);
      expect(result).toStrictEqual(err(Skipped({ attention: false, message: 'actions.balances.blockchain_accounts_add.skipped.existed' })));
    });

    it('should settle failed, naming the chains, when it could be tracked on none of its active chains', async () => {
      whenOk({ failed: { '0xabc': ['eth', 'base'] } });
      const { useAccountAdditions } = await importModule();
      const result = await useAccountAdditions().addEvmAccount(payload);
      assert(isErr(result));
      expect(result.error).toStrictEqual(TaskFailed({
        message: 'actions.balances.blockchain_accounts_add.error.failed_chains::name:eth, name:base',
      }));
    });

    it('should mark the addition as user started only when the caller says so', async () => {
      whenOk({ added: { '0xabc': ['eth'] } });
      const { useAccountAdditions } = await importModule();
      await useAccountAdditions().addEvmAccount(payload, { userStarted: true });
      await useAccountAdditions().addEvmAccount(payload);
      expect(submitTask.mock.calls.map(([spec]) => spec.userStarted)).toStrictEqual([true, undefined]);
    });

    it('should return the failure as a value on an actionable failure', async () => {
      whenActionable('nope');
      const { useAccountAdditions } = await importModule();
      expect(isErr(await useAccountAdditions().addEvmAccount(payload))).toBe(true);
    });

    it('should return an error, not an empty object, on a cancelled task', async () => {
      whenCancelled();
      const { useAccountAdditions } = await importModule();
      const result = await useAccountAdditions().addEvmAccount(payload);
      assert(isErr(result));
      expect(result).not.toStrictEqual(ok({}));
    });
  });
});
