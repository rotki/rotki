import { runSpecWith } from '@test/utils/mocks/native-task';
import { err, ok, type Result } from 'plainfp/result';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import '@test/i18n';

const mocks = vi.hoisted(() => ({
  deleteXpub: vi.fn(),
  notifyError: vi.fn(),
  removeAgnosticBlockchainAccount: vi.fn(),
  removeBlockchainAccount: vi.fn(),
}));

vi.mock('@/modules/accounts/api/use-blockchain-accounts-api', () => ({
  useBlockchainAccountsApi: vi.fn(() => ({
    deleteXpub: mocks.deleteXpub,
    removeAgnosticBlockchainAccount: mocks.removeAgnosticBlockchainAccount,
    removeBlockchainAccount: mocks.removeBlockchainAccount,
  })),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  getErrorMessage: (e: unknown): string => (e instanceof Error ? e.message : String(e)),
  useNotifications: vi.fn(() => ({ notifyError: mocks.notifyError })),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn() },
}));

const runTaskResult = vi.fn();
const submitTask = vi.fn(runSpecWith(runTaskResult));

vi.mock('@/modules/task-center/use-native-task', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useNativeTask: vi.fn(() => ({ cancelByType: vi.fn(() => vi.fn()), runTaskResult, statusOf: vi.fn(), submitTask })),
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

async function importModule(): Promise<typeof import('./use-account-removals')> {
  return import('./use-account-removals');
}

type Removals = ReturnType<Awaited<ReturnType<typeof importModule>>['useAccountRemovals']>;

describe('useAccountRemovals', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // Asserted on the *submitted spec*, not on the descriptor. Declaring `lane` on the activity and
  // asserting `laneOf` there both passed while every removal still went out on the default lane,
  // because no call site forwarded it — so the family caps were dead config and removals that used
  // to run one at a time all raced. Only reading what `submitTask` received can catch that.
  describe('lane', () => {
    const cases: [string, (accounts: Removals) => Promise<void>, string][] = [
      ['removeAccount', async (accounts): Promise<void> => accounts.removeAccount({ accounts: ['0xabc'], chain: 'eth' }), 'accounts-remove:eth'],
      ['deleteXpub', async (accounts): Promise<void> => accounts.deleteXpub({ chain: 'btc', xpub: 'xpub123' }), 'accounts-remove:btc'],
      ['removeAgnosticAccount', async (accounts): Promise<void> => accounts.removeAgnosticAccount('evm', '0xabc'), 'accounts-remove:evm'],
    ];

    it.each(cases)('should submit %s on its own removal lane', async (_name, act, lane) => {
      whenOk({ perAccount: {}, totals: { assets: {}, liabilities: {} } }, false);
      const { useAccountRemovals } = await importModule();

      await act(useAccountRemovals());

      expect(submitTask).toHaveBeenCalledWith(expect.objectContaining({ lane }));
    });
  });

  describe('removeAccount', () => {
    it('should not notify on success', async () => {
      whenOk({ perAccount: {}, totals: { assets: {}, liabilities: {} } }, false);
      const { useAccountRemovals } = await importModule();
      await useAccountRemovals().removeAccount({ accounts: ['0xabc'], chain: 'eth' });
      expect(mocks.notifyError).not.toHaveBeenCalled();
    });

    // Same hazard as the add side: an account delete and an xpub delete on one chain both used
    // `accounts:remove:<chain>`, so an overlap deduped the second onto the first while the UI
    // still dropped its rows, and accounts that were never deleted reappear on the next fetch.
    it('should give a plain removal and an xpub removal distinct activity ids', async () => {
      whenOk({ perAccount: {}, totals: { assets: {}, liabilities: {} } }, false);
      const { useAccountRemovals } = await importModule();
      const accounts = useAccountRemovals();

      await accounts.removeAccount({ accounts: ['0xabc'], chain: 'btc' });
      await accounts.deleteXpub({ chain: 'btc', xpub: 'xpub123' });

      const [first, second] = submitTask.mock.calls.map(([spec]) => spec.id);
      expect(first).not.toBe(second);
    });

    it('should notify on an actionable failure', async () => {
      whenActionable('remove failed');
      const { useAccountRemovals } = await importModule();
      await useAccountRemovals().removeAccount({ accounts: ['0xabc'], chain: 'eth' });
      expect(mocks.notifyError).toHaveBeenCalledOnce();
    });
  });

  describe('removeAgnosticAccount', () => {
    // Keyed by the account category alone, two removals under one category were the same activity,
    // so `submitTask` handed the second the first's promise and the second address was never sent
    // while the UI dropped its row. The same collision the chain-scoped removals had.
    it('should give each address its own activity id within a category', async () => {
      whenOk({ perAccount: {}, totals: { assets: {}, liabilities: {} } }, false);
      const { useAccountRemovals } = await importModule();
      const accounts = useAccountRemovals();

      await accounts.removeAgnosticAccount('evm', '0xabc');
      await accounts.removeAgnosticAccount('evm', '0xdef');

      const [first, second] = submitTask.mock.calls.map(([spec]) => spec.id);
      expect(first).not.toBe(second);
    });

    it('should notify on an actionable failure', async () => {
      whenActionable('agnostic failed');
      const { useAccountRemovals } = await importModule();
      await useAccountRemovals().removeAgnosticAccount('evm', '0xabc');
      expect(mocks.notifyError).toHaveBeenCalledOnce();
    });
  });

  describe('deleteXpub', () => {
    it('should notify on an actionable failure', async () => {
      whenActionable('xpub failed');
      const { useAccountRemovals } = await importModule();
      await useAccountRemovals().deleteXpub({ chain: 'btc', xpub: 'xpub123' });
      expect(mocks.notifyError).toHaveBeenCalledOnce();
    });

    it('should not notify on success', async () => {
      whenOk(true, false);
      const { useAccountRemovals } = await importModule();
      await useAccountRemovals().deleteXpub({ chain: 'btc', xpub: 'xpub123' });
      expect(mocks.notifyError).not.toHaveBeenCalled();
    });
  });
});
