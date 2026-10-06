import { runSpecWith, type SubmittedSpec } from '@test/utils/mocks/native-task';
import { createPinia, setActivePinia } from 'pinia';
import { err, ok } from 'plainfp/result';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useDetectedAccountsStore } from '@/modules/accounts/use-detected-accounts-store';
import { TaskFailed } from '@/modules/core/tasks/task-result';
import '@test/i18n';

const h = vi.hoisted(() => {
  /** The tracked addresses per chain, which a test changes to stand for what the re-read finds. */
  const tracked: Record<string, string[]> = {};
  return {
    detectEvmAccounts: vi.fn(),
    fetchAccounts: vi.fn(),
    notifyError: vi.fn(),
    pending: vi.fn<() => Promise<void> | undefined>(),
    runTaskResult: vi.fn(),
    tracked,
  };
});

const submitTask = vi.fn(runSpecWith(h.runTaskResult));

vi.mock('@/modules/accounts/api/use-blockchain-accounts-api', () => ({
  useBlockchainAccountsApi: vi.fn(() => ({ detectEvmAccounts: h.detectEvmAccounts })),
}));

vi.mock('@/modules/accounts/use-account-load-state', () => ({
  useAccountLoadState: vi.fn(() => ({ pending: h.pending })),
}));

vi.mock('@/modules/accounts/use-account-operations', () => ({
  useAccountOperations: vi.fn(() => ({ fetchAccounts: h.fetchAccounts })),
}));

vi.mock('@/modules/balances/blockchain/use-account-addresses', () => ({
  useAccountAddresses: vi.fn(() => ({ getAddresses: (chain: string): string[] => h.tracked[chain] ?? [] })),
}));

vi.mock('@/modules/core/common/use-supported-chains', async () => {
  const vue = await import('vue');
  return {
    useSupportedChains: vi.fn(() => ({
      evmAndEvmLikeTxChainsInfo: vue.ref([{ id: 'eth' }, { id: 'optimism' }, { id: 'base' }]),
    })),
  };
});

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn(() => ({ notifyError: h.notifyError })),
}));

vi.mock('@/modules/task-center/use-native-task', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useNativeTask: vi.fn(() => ({ submitTask })),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn() },
}));

async function detect(): Promise<void> {
  const { useEvmAccountDetection } = await import('./use-evm-account-detection');
  await useEvmAccountDetection().detectEvmAccounts();
}

describe('useEvmAccountDetection', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    h.fetchAccounts.mockResolvedValue(undefined);
    h.tracked = { eth: ['0xabc'] };
    h.runTaskResult.mockResolvedValue(ok(true));
  });

  it('should report the accounts the run started tracking, and only those', async () => {
    h.fetchAccounts.mockImplementation(async () => {
      h.tracked = { base: ['0xabc'], eth: ['0xabc'], optimism: ['0xabc'] };
    });

    await detect();

    expect(useDetectedAccountsStore().lastRun).toEqual([
      { address: '0xabc', chain: 'optimism' },
      { address: '0xabc', chain: 'base' },
    ]);
  });

  it('should mark what the run found for the accounts table', async () => {
    h.fetchAccounts.mockImplementation(async () => {
      h.tracked = { eth: ['0xabc'], optimism: ['0xabc'] };
    });

    await detect();

    const store = useDetectedAccountsStore();
    expect(store.isDetected('optimism', '0xabc')).toBe(true);
    expect(store.isDetected('eth', '0xabc')).toBe(false);
  });

  it('should report an empty run as finding nothing', async () => {
    await detect();

    expect(useDetectedAccountsStore().lastRun).toEqual([]);
  });

  it('should re-read the detection chains before comparing', async () => {
    await detect();

    expect(h.fetchAccounts).toHaveBeenCalledWith({ blockchain: ['eth', 'optimism', 'base'] });
    expect(h.runTaskResult.mock.invocationCallOrder[0]).toBeLessThan(h.fetchAccounts.mock.invocationCallOrder[0]);
  });

  it('should leave an actionable failure to its dock row and leave no result', async () => {
    h.runTaskResult.mockResolvedValue(err(TaskFailed({ message: 'detect failed' })));

    await detect();

    expect(h.notifyError).not.toHaveBeenCalled();
    expect(h.fetchAccounts).not.toHaveBeenCalled();
    expect(useDetectedAccountsStore().lastRun).toBeUndefined();
  });

  it('should not notify on success', async () => {
    await detect();

    expect(h.notifyError).not.toHaveBeenCalled();
  });

  describe('the task dock', () => {
    function submittedSpec(): SubmittedSpec {
      const spec = submitTask.mock.calls[0]?.[0];
      assert(spec);
      return spec;
    }

    it('should mark what a retry from the dock finds, which re-runs only the task body', async () => {
      h.runTaskResult.mockResolvedValueOnce(err(TaskFailed({ message: 'detect failed' })));
      await detect();
      h.fetchAccounts.mockImplementation(async () => {
        h.tracked = { eth: ['0xabc'], optimism: ['0xabc'] };
      });

      await submittedSpec().run({ cancelled: () => false, report: () => {}, runTask: h.runTaskResult });

      const store = useDetectedAccountsStore();
      expect(store.isDetected('optimism', '0xabc')).toBe(true);
      expect(store.lastRun).toEqual([{ address: '0xabc', chain: 'optimism' }]);
    });

    it('should not start detection on the backend when cancelled while waiting for the account load', async () => {
      let isCancelled = false;
      h.pending.mockImplementation(async () => {
        isCancelled = true;
      });
      submitTask.mockImplementationOnce(async spec => spec.run({ cancelled: () => isCancelled, report: () => {}, runTask: h.runTaskResult }));

      await detect();

      expect(h.runTaskResult).not.toHaveBeenCalled();
      expect(useDetectedAccountsStore().lastRun).toBeUndefined();
    });

    it('should record nothing for a run the user cancelled', async () => {
      h.fetchAccounts.mockImplementation(async () => {
        h.tracked = { eth: ['0xabc'], optimism: ['0xabc'] };
      });
      submitTask.mockImplementationOnce(async spec => spec.run({ cancelled: () => true, report: () => {}, runTask: h.runTaskResult }));

      await detect();

      const store = useDetectedAccountsStore();
      expect(store.isDetected('optimism', '0xabc')).toBe(false);
      expect(store.lastRun).toBeUndefined();
    });
  });

  describe('a manual addition overlapping the run', () => {
    it('should not claim an addition submitted during the run', async () => {
      h.fetchAccounts.mockImplementation(async () => {
        h.tracked = { base: ['0xabc'], eth: ['0xabc', '0xnew'], optimism: ['0xabc'] };
      });
      h.runTaskResult.mockImplementation(async () => {
        useDetectedAccountsStore().startUserAddition('eth', ['0xNEW']);
        return ok(true);
      });

      await detect();

      expect(useDetectedAccountsStore().lastRun).toEqual([
        { address: '0xabc', chain: 'optimism' },
        { address: '0xabc', chain: 'base' },
      ]);
    });

    it('should not claim an addition submitted before the run and still unanswered when it began', async () => {
      useDetectedAccountsStore().startUserAddition(undefined, ['0xNEW']);
      h.fetchAccounts.mockImplementation(async () => {
        h.tracked = { eth: ['0xabc', '0xnew'], optimism: ['0xnew'] };
      });

      await detect();

      expect(useDetectedAccountsStore().lastRun).toEqual([]);
    });

    it('should claim again what an addition finished before the run added', async () => {
      const store = useDetectedAccountsStore();
      store.finishUserAddition(store.startUserAddition('optimism', ['0xabc']));
      h.fetchAccounts.mockImplementation(async () => {
        h.tracked = { eth: ['0xabc'], optimism: ['0xabc'] };
      });

      await detect();

      expect(store.lastRun).toEqual([{ address: '0xabc', chain: 'optimism' }]);
    });
  });

  it('should wait for the account load before the snapshot, so accounts not read yet are not found', async () => {
    h.tracked = {};
    const load = new Promise<void>((resolve) => {
      setTimeout(() => {
        h.tracked = { eth: ['0xabc'] };
        resolve();
      }, 0);
    });
    h.pending.mockReturnValue(load);
    h.runTaskResult.mockImplementation(async () => {
      await load;
      return ok(true);
    });

    await detect();

    expect(useDetectedAccountsStore().lastRun).toEqual([]);
  });
});
