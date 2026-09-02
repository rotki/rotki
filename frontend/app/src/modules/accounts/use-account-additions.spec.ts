import { runSpecWith } from '@test/utils/mocks/native-task';
import { err, isErr, ok, type Result } from 'plainfp/result';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { type AccountPayload, type XpubAccountPayload, XpubKeyType } from '@/modules/accounts/blockchain-accounts';
import { Cancelled, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
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

  describe('addEvmAccount', () => {
    const payload: AccountPayload = { address: '0xabc', tags: null };

    it('should return the result on success', async () => {
      whenOk({ added: { eth: ['0xabc'] } });
      const { useAccountAdditions } = await importModule();
      const result = await useAccountAdditions().addEvmAccount(payload);
      expect(mocks.addEvmAccount).toHaveBeenCalledWith(payload);
      expect(result).toStrictEqual(ok({ added: { eth: ['0xabc'] } }));
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
