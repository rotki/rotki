import type { TaskMeta } from '@/modules/tasks/types';
import { Blockchain } from '@rotki/common';
import { isEqual } from 'es-toolkit';
import { usePremium } from '@/composables/premium';
import { useStatusUpdater } from '@/composables/status';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { Module } from '@/modules/common/modules';
import { Section, Status } from '@/modules/common/status';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { TaskType } from '@/modules/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/tasks/use-task-handler';
import { useTaskStore } from '@/modules/tasks/use-task-store';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { logger } from '@/utils/logging';
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
  const { activeModules } = storeToRefs(useGeneralSettingsStore());

  const premium = usePremium();
  const { t } = useI18n({ useScope: 'global' });

  const { getSushiswapBalances, getUniswapV2Balances } = usePoolApi();
  const { runTask } = useTaskHandler();
  const { isTaskRunning } = useTaskStore();

  function handleFailure(taskType: TaskType, outcome: { message: string; error?: unknown }, title: string, protocol: string): void {
    logger.error(`action failure for task ${TaskType[taskType]}:`, outcome.error);
    const { notifyError } = useNotifications();
    notifyError(title, t('modules.dashboard.liquidity_pools.task.error_message', { message: outcome.message, protocol }));
  }

  async function retrieveUniswapV2Balances(refresh = false): Promise<void> {
    if (!get(activeModules).includes(Module.UNISWAP))
      return;

    const { getStatus, setStatus } = useStatusUpdater(Section.POOLS_UNISWAP_V2);

    if (isTaskRunning(TaskType.UNISWAP_V2_BALANCES) || (getStatus() === Status.LOADED && !refresh))
      return;

    setStatus(refresh ? Status.REFRESHING : Status.LOADING);

    const title = t('modules.dashboard.liquidity_pools.task.title', { protocol: 'Uniswap V2' });
    const outcome = await runTask<PoolBalances, TaskMeta>(
      async () => getUniswapV2Balances(),
      { type: TaskType.UNISWAP_V2_BALANCES, meta: { title }, guard: false },
    );

    if (outcome.success) {
      set(uniswapPoolBalances, PoolBalances.parse(outcome.result));
    }
    else if (isActionableFailure(outcome)) {
      handleFailure(TaskType.UNISWAP_V2_BALANCES, outcome, title, 'Uniswap V2');
    }

    setStatus(Status.LOADED);
  }

  async function retrieveSushiswapBalances(refresh = false): Promise<void> {
    if (!get(activeModules).includes(Module.SUSHISWAP))
      return;

    const { getStatus, setStatus } = useStatusUpdater(Section.POOLS_SUSHISWAP);

    if (isTaskRunning(TaskType.SUSHISWAP_BALANCES) || (getStatus() === Status.LOADED && !refresh))
      return;

    setStatus(refresh ? Status.REFRESHING : Status.LOADING);

    const title = t('modules.dashboard.liquidity_pools.task.title', { protocol: 'Sushiswap' });
    const outcome = await runTask<PoolBalances, TaskMeta>(
      async () => getSushiswapBalances(),
      { type: TaskType.SUSHISWAP_BALANCES, meta: { title }, guard: false },
    );

    if (outcome.success) {
      set(sushiswapPoolBalances, PoolBalances.parse(outcome.result));
    }
    else if (isActionableFailure(outcome)) {
      handleFailure(TaskType.SUSHISWAP_BALANCES, outcome, title, 'Sushiswap');
    }

    setStatus(Status.LOADED);
  }

  async function fetch(refresh = false): Promise<void> {
    if (get(ethAddresses).length <= 0)
      return;

    await retrieveUniswapV2Balances(refresh);
    if (!get(premium))
      return;

    await retrieveSushiswapBalances(refresh);
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
