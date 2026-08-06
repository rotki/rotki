import type { Ref } from 'vue';
import { Blockchain } from '@rotki/common';
import { isEqual } from 'es-toolkit';
import { map as mapResult, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { logger } from '@/modules/core/common/logging/logging';
import { Module } from '@/modules/core/common/modules';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { onActionableError, type TaskError } from '@/modules/core/tasks/task-result';
import { usePremium } from '@/modules/premium/use-premium';
import { useSetting } from '@/modules/settings/use-setting';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';
import { PoolBalances } from './types';
import { usePoolApi } from './use-pool-api';
import { usePoolBalancesStore } from './use-pool-balances-store';

interface UsePoolDataFetchingReturn {
  fetch: (refresh?: boolean) => Promise<void>;
}

export function usePoolDataFetching(): UsePoolDataFetchingReturn {
  const { addresses } = useAccountAddresses();
  const ethAddresses = computed<string[]>(() => get(addresses)[Blockchain.ETH] ?? []);

  const { sushiswapPoolBalances, uniswapPoolBalances } = storeToRefs(usePoolBalancesStore());
  const { recentlyAddedAddresses } = storeToRefs(useBlockchainAccountsStore());
  const activeModules = useSetting('activeModules');

  const premium = usePremium();
  const { t } = useI18n({ useScope: 'global' });

  const { getSushiswapBalances, getUniswapV2Balances } = usePoolApi();
  const { statusOf, submitTask } = useNativeTask();
  const { notifyError } = useNotifications();

  /**
   * The two protocols differ only in module gate, task type, endpoint and target ref, so they
   * share one native submission. Each is a singleton activity (`liquidity-pools:<protocol>`);
   * the old `isTaskRunning || (LOADED && !refresh)` gate becomes the orchestrator's `active` and
   * `everCompleted`.
   */
  interface Protocol {
    readonly module: Module;
    readonly part: ActivityPart;
    readonly label: string;
    readonly query: () => Promise<{ taskId: number }>;
    readonly target: Ref<PoolBalances>;
  }

  async function retrievePoolBalances(protocol: Protocol, refresh: boolean): Promise<void> {
    if (!get(activeModules).includes(protocol.module))
      return;

    const status = statusOf(ActivityKind.LIQUIDITY_POOLS, protocol.part);
    if (status.active || (status.everCompleted && !refresh))
      return;

    const title = t('modules.dashboard.liquidity_pools.task.title', { protocol: protocol.label });

    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.LIQUIDITY_POOLS, protocol.part),
      kind: ActivityKind.LIQUIDITY_POOLS,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<PoolBalances>(
          async () => protocol.query(),
        ),
        (result) => {
          set(protocol.target, PoolBalances.parse(result));
        },
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.liquidity_pools.protocol'), { protocol: protocol.label }),
      title: t('task_center.group.liquidity_pools'),
    });

    onActionableError(outcome, (error) => {
      logger.error(`action failure for ${protocol.label}:`, error.message);
      notifyError(title, t('modules.dashboard.liquidity_pools.task.error_message', {
        message: error.message,
        protocol: protocol.label,
      }));
    });
  }

  const uniswapV2: Protocol = {
    label: 'Uniswap V2',
    module: Module.UNISWAP,
    part: ActivityPart.UNISWAP_V2,
    query: getUniswapV2Balances,
    target: uniswapPoolBalances,
  };

  const sushiswap: Protocol = {
    label: 'Sushiswap',
    module: Module.SUSHISWAP,
    part: ActivityPart.SUSHISWAP,
    query: getSushiswapBalances,
    target: sushiswapPoolBalances,
  };

  async function fetch(refresh = false): Promise<void> {
    if (get(ethAddresses).length === 0)
      return;

    await retrievePoolBalances(uniswapV2, refresh);
    if (!get(premium))
      return;

    await retrievePoolBalances(sushiswap, refresh);
  }

  watch(ethAddresses, async (current, previous) => {
    if (isEqual(current, previous))
      return;

    const added = current.filter(a => !previous.includes(a));
    const removed = previous.filter(a => !current.includes(a));
    const recent = get(recentlyAddedAddresses);

    if (removed.length === 0 && added.length > 0 && added.every(a => recent.has(a)))
      return;

    await fetch(true);
  });

  watch(premium, async (isActive, wasActive) => {
    if (wasActive !== isActive)
      await fetch(true);
  });

  return {
    fetch,
  };
}
