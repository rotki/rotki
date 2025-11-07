import type { AddAccountsPayload, XpubAccountPayload } from '@/types/blockchain/accounts';
import type { ChainAddress } from '@/types/history/events';
import { Severity } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useAccountAdditionService } from '@/composables/blockchain/use-account-addition-service';
import { type RefreshAccountsParams, useAccountOperations } from '@/composables/blockchain/use-account-operations';
import { useSupportedChains } from '@/composables/info/chains';
import { useNotificationsStore } from '@/store/notifications';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { logger } from '@/utils/logging';

interface AddAccountsOption {
  wait: boolean;
}

interface UseBlockchainsReturn {
  addAccounts: (chain: string, data: AddAccountsPayload | XpubAccountPayload, options?: AddAccountsOption) => Promise<void>;
  addEvmAccounts: (payload: AddAccountsPayload, options?: AddAccountsOption) => Promise<void>;
  detectEvmAccounts: () => Promise<void>;
  fetchAccounts: (blockchain?: string | string[], refreshEns?: boolean) => Promise<void>;
  refreshAccounts: (params?: RefreshAccountsParams) => Promise<void>;
}

export function useBlockchains(): UseBlockchainsReturn {
  // Use services for complex logic
  const accountAdditionService = useAccountAdditionService();
  const { detectEvmAccounts, fetchAccounts, refreshAccounts } = useAccountOperations();

  // Keep essential stores and composables
  const { getChainName } = useSupportedChains();
  const { isTaskRunning } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { t } = useI18n({ useScope: 'global' });

  const addEvmAccounts = async (payload: AddAccountsPayload, options?: AddAccountsOption): Promise<void> => {
    const onComplete = async (params: { addedAccounts: any[]; modulesToEnable?: any[] }): Promise<void> =>
      accountAdditionService.completeAccountAddition(params, refreshAccounts);

    if (payload.payload.length === 1) {
      const addResult = await accountAdditionService.addSingleEvmAddress(payload.payload[0]);
      if (addResult.type === 'error')
        throw addResult.error;

      startPromise(onComplete({ addedAccounts: addResult.accounts, modulesToEnable: payload.modules }));
    }
    else {
      if (options?.wait)
        await accountAdditionService.addMultipleEvmAccounts(payload, onComplete);
      else
        startPromise(accountAdditionService.addMultipleEvmAccounts(payload, onComplete));
    }
  };

  const addAccounts = async (chain: string, payload: AddAccountsPayload | XpubAccountPayload, options?: AddAccountsOption): Promise<void> => {
    const taskType = TaskType.ADD_ACCOUNT;
    if (isTaskRunning(taskType)) {
      logger.debug(`${TaskType[taskType]} is already running.`);
      return;
    }

    const isXpub = 'xpub' in payload;
    const modules = isXpub ? [] : payload.modules;

    const filteredPayload = isXpub ? [] : accountAdditionService.getNewAccountPayload(chain, payload.payload);
    if (filteredPayload.length === 0 && !isXpub) {
      const title = t('actions.balances.blockchain_accounts_add.task.title', {
        blockchain: get(getChainName(chain)),
      });
      const message = t('actions.balances.blockchain_accounts_add.no_new.description');
      notify({
        display: true,
        message,
        severity: Severity.INFO,
        title,
      });
      return;
    }

    const onComplete = async (params: { addedAccounts: ChainAddress[]; chain: string; isXpub?: boolean; modulesToEnable?: any[] }): Promise<void> =>
      accountAdditionService.completeAccountAddition(params, refreshAccounts);

    if (filteredPayload.length === 1 || isXpub) {
      const addResult = await accountAdditionService.addSingleAccount(isXpub ? payload : filteredPayload[0], chain);
      if (addResult.type === 'error')
        throw addResult.error;

      startPromise(onComplete({
        addedAccounts: [{
          address: addResult.address,
          chain,
        }],
        chain,
        isXpub,
        modulesToEnable: modules,
      }));
    }
    else {
      if (options?.wait)
        await accountAdditionService.addMultipleAccounts(filteredPayload, chain, modules, onComplete);
      else
        startPromise(accountAdditionService.addMultipleAccounts(filteredPayload, chain, modules, onComplete));
    }
  };

  return {
    addAccounts,
    addEvmAccounts,
    detectEvmAccounts,
    fetchAccounts,
    refreshAccounts,
  };
}
