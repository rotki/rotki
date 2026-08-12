import type { RefreshMode } from '@/modules/balances/types/refresh-mode';
import type { EvmChainInfo, SupportedChains } from '@/modules/core/api/types/chains';
import { Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { createCustomPinia } from '@test/utils/create-pinia';
import { runSpecWith, type SubmittedSpec } from '@test/utils/mocks/native-task';
import { hasTag } from 'plainfp/tagged';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { createAccount } from '@/modules/accounts/create-account';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBlockchainBalancesApi } from '@/modules/balances/api/use-blockchain-balances-api';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';

vi.mock('@/modules/core/notifications/use-notifications-store', () => ({
  useNotificationsStore: vi.fn().mockReturnValue({}),
}));

vi.mock('@/modules/balances/use-balances-store', () => ({
  useBalancesStore: vi.fn().mockReturnValue({
    updateBalances: vi.fn(),
  }),
}));

const detectForChain = vi.fn<(chain: string, parent: string) => Promise<void>>(async () => {});

vi.mock('@/modules/balances/blockchain/use-token-detection-orchestrator', () => ({
  useTokenDetectionOrchestrator: vi.fn(() => ({ detectForChain })),
}));

vi.mock('@/modules/balances/api/use-blockchain-balances-api', () => ({
  useBlockchainBalancesApi: vi.fn().mockReturnValue({
    queryBlockchainBalances: vi.fn().mockResolvedValue({ taskId: 1 }),
    refreshBlockchainBalances: vi.fn().mockResolvedValue({ taskId: 4 }),
    queryXpubBalances: vi.fn().mockResolvedValue({ taskId: 3 }),
  }),
}));

vi.mock('@/modules/core/tasks/use-task-handler', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useTaskHandler: vi.fn().mockReturnValue({
    // Blockchain balances run native via runTaskResult (plainfp Result).
    runTaskResult: vi.fn().mockImplementation(async (taskFn: () => Promise<unknown>) => {
      await taskFn();
      const { ok } = await import('plainfp/result');
      return ok({
        perAccount: {},
        totals: {
          assets: {},
          liabilities: {},
        },
      });
    }),
  }),
}));

// The balance processing service takes its runner from the activity, so the stub passes one that
// resolves like the backend task would.
//
// `submitTask` and `supersedeTask` are separate stubs that both run the spec inline. The real
// difference between them (cancel, await the cancelled promise, resubmit) belongs to
// `useNativeTask` and is covered by its own spec; what this file owns is which of the two a given
// refresh mode routes to.
const { runTask } = vi.hoisted(() => ({ runTask: vi.fn() }));
const submitTask = vi.fn();
const supersedeTask = vi.fn();

vi.mock('@/modules/task-center/use-native-task', async () => {
  const { ok } = await import('plainfp/result');
  runTask.mockImplementation(async (taskFn: () => Promise<unknown>) => {
    await taskFn();
    return ok({ perAccount: {}, totals: { assets: {}, liabilities: {} } });
  });

  return {
    useNativeTask: vi.fn(() => ({
      reportProgress: vi.fn(),
      submitTask,
      supersedeTask,
    })),
  };
});

vi.mock('@/modules/core/common/use-supported-chains', async () => {
  const { computed } = await import('vue');
  const { Blockchain } = await import('@rotki/common');
  return ({
    useSupportedChains: vi.fn().mockReturnValue({
      getChain: (chain: string) => chain,
      getChainAccountType: (chain: Blockchain) => chain === Blockchain.BTC ? 'bitcoin' : 'evm',
      getChainImageUrl: (chain: Blockchain) => `${chain}.png`,
      getChainName: (chain: Blockchain) => chain === Blockchain.BTC ? 'Bitcoin' : 'Ethereum',
      getNativeAsset: (chain: Blockchain) => chain,
      supportedChains: computed<SupportedChains>(() => [
        {
          evmChainName: 'ethereum',
          id: Blockchain.ETH,
          image: '',
          name: 'Ethereum',
          nativeToken: 'ETH',
          type: 'evm',
        } satisfies EvmChainInfo,
        {
          id: Blockchain.BTC,
          image: '',
          name: 'Bitcoin',
          type: 'bitcoin',
        },
      ]),
    }),
  });
});

describe('useBlockchainBalances', () => {
  function setDisabled(value: Record<string, string[]>): void {
    const repo = useSettingsRepo();
    repo.updateGeneral({ ...repo.general, disabledChainQueries: value });
  }

  let api: ReturnType<typeof useBlockchainBalancesApi>;
  let blockchainBalances: ReturnType<typeof useBlockchainBalances>;

  beforeEach(() => {
    setActivePinia(createCustomPinia());
    api = useBlockchainBalancesApi();
    blockchainBalances = useBlockchainBalances();
    vi.clearAllMocks();
    detectForChain.mockReset().mockResolvedValue(undefined);
    submitTask.mockImplementation(runSpecWith(runTask));
    supersedeTask.mockImplementation(runSpecWith(runTask));
  });

  describe('refreshBlockchainBalances', () => {
    beforeEach(() => {
      // refresh only calls the api when the chain has an account (see executeBalanceQuery);
      // add one per test so these cases don't rely on state left by a sibling test.
      const { updateAccounts } = useBlockchainAccountsStore();
      updateAccounts(Blockchain.ETH, [
        createAccount(
          { address: '0x49ff149D649769033d43783E7456F626862CD160', label: null, tags: null },
          { chain: Blockchain.ETH, nativeAsset: 'ETH' },
        ),
      ]);
    });

    it('should refresh particular blockchain - default', () => {
      const call = async (mode: RefreshMode = 'periodic'): Promise<void> => {
        await blockchainBalances.refreshBlockchainBalances(
          {
            blockchain: Blockchain.ETH,
          },
          mode,
        );
      };

      const assert = (times = 1): void => {
        expect(api.refreshBlockchainBalances).toHaveBeenCalledTimes(times);
        expect(api.refreshBlockchainBalances).toHaveBeenCalledWith({
          addresses: undefined,
          blockchain: Blockchain.ETH,
          isXpub: false,
        });
      };

      startPromise(call());
      assert();
    });

    it('should ignore periodic balance refresh, when there are other task running', async () => {
      const call = async (mode: RefreshMode = 'periodic'): Promise<void> => {
        await blockchainBalances.refreshBlockchainBalances(
          {
            blockchain: Blockchain.ETH,
          },
          mode,
        );
      };

      const assert = (times = 1): void => {
        expect(api.refreshBlockchainBalances).toHaveBeenCalledTimes(times);
        expect(api.refreshBlockchainBalances).toHaveBeenCalledWith({
          addresses: undefined,
          blockchain: Blockchain.ETH,
          isXpub: false,
        });
      };

      const refreshState = useBalanceRefreshState();
      const loading = refreshState.useIsRefreshing(Blockchain.ETH);

      startPromise(call());
      assert(1);

      startPromise(call());
      assert(1);

      await until(loading).toBe(false);
      assert(1);
    });

    /**
     * ⭐ §7. A user pressing refresh on a busy chain supersedes the run in flight instead of
     * joining it, so they get a fresh query with their own parameters rather than the background
     * run's. This replaced an `until(() => isChainRefreshing(chain)).toBe(false)` poll that reached
     * a similar outcome by waiting out work the user had already superseded.
     *
     * The cancel/await/resubmit mechanics live in `useNativeTask` and are covered there; the
     * routing decision is what belongs here.
     */
    it('should supersede a running refresh when the user asks for one', async () => {
      const call = async (mode: RefreshMode): Promise<void> => {
        await blockchainBalances.refreshBlockchainBalances({ blockchain: Blockchain.ETH }, mode);
      };

      await call('periodic');
      expect(submitTask).toHaveBeenCalledTimes(1);
      expect(supersedeTask).not.toHaveBeenCalled();

      await call('user');
      expect(supersedeTask).toHaveBeenCalledTimes(1);
      // Not joined onto the background run: the user's press genuinely re-queried.
      expect(api.refreshBlockchainBalances).toHaveBeenCalledTimes(2);
    });

    it('should join, not supersede, a background refresh', async () => {
      await blockchainBalances.refreshBlockchainBalances({ blockchain: Blockchain.ETH }, 'background');

      expect(submitTask).toHaveBeenCalledTimes(1);
      expect(supersedeTask).not.toHaveBeenCalled();
    });

    /**
     * ⭐ §3. The chain job's body is statement order: detection, then the query that reads what it
     * found. Not a `deps` edge between two activities — one job, two stages.
     */
    it('should detect before querying, as children of the chain job', async () => {
      const order: string[] = [];
      detectForChain.mockImplementation(async () => {
        order.push('detect');
      });
      vi.mocked(api.refreshBlockchainBalances).mockImplementation(async () => {
        order.push('query');
        return { taskId: 4 };
      });

      await blockchainBalances.refreshBlockchainBalances({ blockchain: Blockchain.ETH }, 'background', { detect: true });

      expect(order).toStrictEqual(['detect', 'query']);
      // Parented to the chain job, which is what makes cancelling the chain stop its addresses.
      // 🔴 The id carries `detect`: sharing it with a plain refresh let `submitTask`'s dedup join
      // this run to one that does no detection, silently skipping the sweep for that chain.
      expect(detectForChain).toHaveBeenCalledWith(
        Blockchain.ETH,
        makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, Blockchain.ETH, ActivityPart.DETECT),
        undefined,
      );
    });

    /**
     * ⭐ Account addition and account migration are the flows that know which addresses are new, and
     * detecting the chain's other fifty on their behalf is work nobody asked for. Without the
     * forward the option is silently inert — the call still succeeds and still detects everything.
     */
    it('should forward the detection narrowing to the chain job', async () => {
      await blockchainBalances.refreshBlockchainBalances(
        { blockchain: Blockchain.ETH },
        'background',
        { detect: true, detectAddresses: ['0xabc'] },
      );

      // The id carries a digest of the narrowing, so match the parent the job actually submitted
      // rather than restating the id here.
      const [[spec]] = submitTask.mock.calls;
      expect(detectForChain).toHaveBeenCalledWith(Blockchain.ETH, spec.id, ['0xabc']);
    });

    /**
     * 🔴🔴 Two additions on one chain differ only in their narrowing, so a shared id makes the
     * second dedup onto the first and its addresses are never detected. A CSV import starts every
     * row in the same tick, which is exactly this shape.
     */
    it('should not share an id between differently narrowed detections', async () => {
      await blockchainBalances.refreshBlockchainBalances(
        { blockchain: Blockchain.ETH },
        'background',
        { detect: true, detectAddresses: ['0xaaa'] },
      );
      await blockchainBalances.refreshBlockchainBalances(
        { blockchain: Blockchain.ETH },
        'background',
        { detect: true, detectAddresses: ['0xbbb'] },
      );

      const ids = submitTask.mock.calls.map(([spec]) => spec.id);
      expect(new Set(ids).size).toBe(2);
    });

    /** Every reader of this id is prefix-based, so `(kind, chain)` has to keep matching. */
    it('should keep the chain prefix when the detection is narrowed', async () => {
      await blockchainBalances.refreshBlockchainBalances(
        { blockchain: Blockchain.ETH },
        'background',
        { detect: true, detectAddresses: ['0xaaa'] },
      );

      const [[spec]] = submitTask.mock.calls;
      expect(spec.id.startsWith(makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, Blockchain.ETH))).toBe(true);
    });

    /**
     * 🔴🔴 A detecting run and a plain one must not share an id. `submitTask` dedups by id, so a
     * login sweep landing while any background refresh is in flight (wallet transaction, websocket
     * refresh, eth2 watcher) would join it and never detect — no row, no log, no error — while
     * `withDetection` still recorded the sweep, suppressing the next login's too.
     */
    it('should not share an id between a detecting and a plain refresh', async () => {
      await blockchainBalances.refreshBlockchainBalances({ blockchain: Blockchain.ETH }, 'background');
      await blockchainBalances.refreshBlockchainBalances({ blockchain: Blockchain.ETH }, 'background', { detect: true });

      const ids = submitTask.mock.calls.map(([spec]) => spec.id);
      expect(new Set(ids).size).toBe(2);
    });

    /**
     * ⭐ §5. The fan-out is a *run*, and its identity is scope + mode — so two identical runs dedup
     * onto one umbrella while a full refresh and a single-chain one coexist.
     */
    it('should declare the chain jobs under a run umbrella', async () => {
      await blockchainBalances.refreshBlockchainBalances({}, 'background');

      const submitted = submitTask.mock.calls.map(([spec]) => spec.id);
      const umbrella = submitted.find(id => id.includes(`:${ActivityPart.RUN}:`));
      assert(umbrella !== undefined);
      expect(umbrella).toContain('background');

      // Every chain in scope is a child of it, including the one with nothing to query.
      for (const chain of [Blockchain.ETH, Blockchain.BTC]) {
        const child = submitTask.mock.calls.find(([spec]) => spec.id === makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, chain));
        assert(child !== undefined);
        expect(child[0].parent).toBe(umbrella);
      }
    });

    /**
     * 🔴🔴 The umbrella settles COMPLETE whenever its children settle — `allSettled`, so even when
     * every one of them FAILED. Sharing its children's kind meant it wrote a success to the
     * completion ledger, and `statusOf(BLOCKCHAIN_BALANCES).everCompleted` aggregates by kind: the
     * dashboard then read "loaded" after a total failure and showed a settled, empty portfolio.
     */
    it('should mark the run umbrella as a container, so it claims no freshness', async () => {
      await blockchainBalances.refreshBlockchainBalances({}, 'background');

      const umbrella = submitTask.mock.calls
        .map(([spec]) => spec)
        .find(spec => spec.id.includes(`:${ActivityPart.RUN}:`));
      assert(umbrella !== undefined);
      expect(umbrella.container).toBe(true);

      // The chains themselves are subjects and must keep writing their own entries.
      const chainSpec = submitTask.mock.calls
        .map(([spec]) => spec)
        .find(spec => spec.id === makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, Blockchain.ETH));
      assert(chainSpec !== undefined);
      expect(chainSpec.container).toBeUndefined();
    });

    it('should give a run a different identity per scope and per mode', async () => {
      await blockchainBalances.refreshBlockchainBalances({}, 'background');
      await blockchainBalances.refreshBlockchainBalances({}, 'periodic');

      const runs = submitTask.mock.calls
        .map(([spec]) => spec.id)
        .filter(id => id.includes(`:${ActivityPart.RUN}:`));

      // Same scope, different mode — two runs, not one.
      expect(new Set(runs).size).toBe(2);
    });

    /**
     * A parent over one child is a second row describing the same work, so a single-chain refresh
     * has no umbrella at all — the caller never branches on the count.
     */
    it('should not raise an umbrella for a single-chain run', async () => {
      await blockchainBalances.refreshBlockchainBalances({ blockchain: Blockchain.ETH }, 'background');

      const submitted = submitTask.mock.calls.map(([spec]) => spec.id);
      expect(submitted.some(id => id.includes(`:${ActivityPart.RUN}:`))).toBe(false);
      expect(submitted).toContain(makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, Blockchain.ETH));
    });

    /**
     * 🔴🔴 §5. A chain with nothing to query used to return before submitting anything, so it
     * vanished from its run's denominator — "11 of 11" over a scope of 17. It now settles SKIPPED
     * with a reason, which is terminal-but-not-successful and raises no notification.
     */
    it('should settle a chain with no accounts as skipped, not drop it', async () => {
      // btc is in scope but has no accounts in this fixture.
      submitTask.mockImplementation(async (spec: SubmittedSpec) => spec.run({ cancelled: () => false, report: () => {}, runTask }));

      await blockchainBalances.refreshBlockchainBalances({ blockchain: Blockchain.BTC }, 'background');

      // The chain still gets its own activity, so the run's denominator counts it...
      const [spec] = submitTask.mock.calls[0];
      expect(spec.id).toBe(makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, Blockchain.BTC));

      // ...and it settles terminal-but-not-successful, with a reason the task centre can render.
      const result = await submitTask.mock.results[0].value;
      assert(!result.ok);
      expect(hasTag(result.error, 'Skipped')).toBe(true);
      expect(api.refreshBlockchainBalances).not.toHaveBeenCalled();
    });

    /**
     * 🔴🔴 Seen against a real backend. Cancelling Ethereum mid-detection aborted both running
     * children (`DELETE /api/1/tasks/424` and `/425`) and left the other seven addresses never
     * attempted — the cascade doing its job — and then the chain job's own body carried straight
     * on and issued `POST /balances/blockchains/eth` anyway, writing balances and recording a
     * completion for a chain the user had stopped. Nothing can interrupt a running async body, so
     * the body has to ask.
     */
    it('should not query after being cancelled during detection', async () => {
      let stageCancelled = false;
      detectForChain.mockImplementation(async () => {
        // The cancel lands while detection is in flight, exactly as a user click would.
        stageCancelled = true;
      });
      submitTask.mockImplementation(async (spec: SubmittedSpec) =>
        spec.run({ cancelled: () => stageCancelled, report: () => {}, runTask }));

      await blockchainBalances.refreshBlockchainBalances({ blockchain: Blockchain.ETH }, 'background', { detect: true });

      expect(detectForChain).toHaveBeenCalledOnce();
      expect(api.refreshBlockchainBalances).not.toHaveBeenCalled();

      const result = await submitTask.mock.results[0].value;
      assert(!result.ok);
      expect(hasTag(result.error, 'Cancelled')).toBe(true);
    });

    /**
     * ⭐ `disabledChainQueries` reaches the query path, not just the sync panel. Without this the
     * app kept issuing `POST /balances/blockchains/<chain>` and `tokens/detect` for a chain the
     * user switched off — observed against a real backend.
     */
    it('should skip an excluded chain instead of querying or detecting it', async () => {
      setDisabled({ [Blockchain.ETH]: [] });

      await blockchainBalances.refreshBlockchainBalances({ blockchain: Blockchain.ETH }, 'background', { detect: true });

      expect(api.refreshBlockchainBalances).not.toHaveBeenCalled();
      expect(detectForChain).not.toHaveBeenCalled();

      // Submitted, not dropped: the chain is still in the run's scope, so it owes it a row.
      const result = await submitTask.mock.results[0].value;
      assert(!result.ok);
      expect(hasTag(result.error, 'Skipped')).toBe(true);
    });

    it('should still query a chain whose rule only names other addresses', async () => {
      setDisabled({ [Blockchain.ETH]: ['0xdeadbeef'] });

      await blockchainBalances.refreshBlockchainBalances({ blockchain: Blockchain.ETH }, 'background');

      expect(api.refreshBlockchainBalances).toHaveBeenCalledTimes(1);
    });

    it('should narrow the payload to the addresses the rule still allows', async () => {
      setDisabled({ [Blockchain.ETH]: ['0xexcluded'] });

      await blockchainBalances.refreshBlockchainBalances(
        { addresses: ['0xexcluded', '0xallowed'], blockchain: Blockchain.ETH },
        'background',
      );

      expect(api.refreshBlockchainBalances).toHaveBeenCalledWith({
        addresses: ['0xallowed'],
        blockchain: Blockchain.ETH,
        isXpub: false,
      });
    });

    it('should skip a chain whose every requested address is excluded', async () => {
      setDisabled({ [Blockchain.ETH]: ['0xexcluded'] });

      await blockchainBalances.refreshBlockchainBalances(
        { addresses: ['0xexcluded'], blockchain: Blockchain.ETH },
        'background',
      );

      expect(api.refreshBlockchainBalances).not.toHaveBeenCalled();
    });

    it('should match the rule regardless of address case', async () => {
      setDisabled({ [Blockchain.ETH]: ['0XEXCLUDED'] });

      await blockchainBalances.refreshBlockchainBalances(
        { addresses: ['0xexcluded'], blockchain: Blockchain.ETH },
        'background',
      );

      expect(api.refreshBlockchainBalances).not.toHaveBeenCalled();
    });

    it('should not detect when the flow did not ask for it', async () => {
      await blockchainBalances.refreshBlockchainBalances({ blockchain: Blockchain.ETH }, 'background');

      expect(detectForChain).not.toHaveBeenCalled();
      expect(api.refreshBlockchainBalances).toHaveBeenCalledTimes(1);
    });

    it('should refresh balances with isXpub flag set to true', async () => {
      const { updateAccounts } = useBlockchainAccountsStore();

      // Add a BTC account first
      updateAccounts(Blockchain.BTC, [
        createAccount(
          { address: 'xpub6CUGRUonZSQ4TWtTMmzXdrXDtypWKiKrhko4egpiMZbpiaQL2jkwSB1icqYh2cfDfVxdx4df189oLKnC5fSwqPfgyP3hooxujYzAu3fDVmz', label: null, tags: null },
          { chain: Blockchain.BTC, nativeAsset: 'BTC' },
        ),
      ]);

      await blockchainBalances.refreshBlockchainBalances({
        blockchain: Blockchain.BTC,
        isXpub: true,
      });

      expect(api.queryXpubBalances).toHaveBeenCalledWith({
        addresses: undefined,
        blockchain: Blockchain.BTC,
        isXpub: true,
      });
    });
  });
});
