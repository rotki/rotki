import type { AddAccountsPayload, XpubAccountPayload } from '@/modules/accounts/blockchain-accounts';
import type { ChainAddress } from '@/modules/history/events/event-payloads';
import { startPromise } from '@shared/utils';
import { isErr } from 'plainfp/result';
import { useAccountAdditionService } from '@/modules/accounts/use-account-addition-service';
import { type RefreshAccountsParams, useAccountOperations } from '@/modules/accounts/use-account-operations';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { throwIfActionable } from '@/modules/core/tasks/task-result';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

interface AddAccountsOption {
  wait: boolean;
}

interface UseBlockchainAccountManagementReturn {
  addAccounts: (chain: string, data: AddAccountsPayload | XpubAccountPayload, options?: AddAccountsOption) => Promise<void>;
  addEvmAccounts: (payload: AddAccountsPayload, options?: AddAccountsOption) => Promise<void>;
  detectEvmAccounts: () => Promise<void>;
  fetchAccounts: (blockchain?: string | string[], refreshEns?: boolean) => Promise<void>;
  refreshAccounts: (params?: RefreshAccountsParams) => Promise<void>;
}

export function useBlockchainAccountManagement(): UseBlockchainAccountManagementReturn {
  // Use services for complex logic
  const accountAdditionService = useAccountAdditionService();
  const { detectEvmAccounts, fetchAccounts, refreshAccounts } = useAccountOperations();

  // Keep essential stores and composables
  const { getChainName } = useSupportedChains();
  const { useWorkStatusPrefix } = useTaskCenter();
  const addRunning = useWorkStatusPrefix(ActivityKind.ACCOUNTS, ActivityPart.ADD);
  const { notifyInfo } = useNotifications();
  const { t } = useI18n({ useScope: 'global' });

  const addEvmAccounts = async (payload: AddAccountsPayload, options?: AddAccountsOption): Promise<void> => {
    const onComplete = async (params: { addedAccounts: any[]; modulesToEnable?: any[] }): Promise<void> =>
      accountAdditionService.completeAccountAddition(params, refreshAccounts, fetchAccounts);

    if (payload.payload.length === 1) {
      const addResult = await accountAdditionService.addSingleEvmAddress(payload.payload[0]);
      // The form awaits this call to keep its dialog open on failure, so a real error is still
      // raised as a throw; only the internal plumbing carries it as a value. A cancellation
      // returns silently: the user asked for it, so an error dialog would be wrong.
      if (isErr(addResult)) {
        throwIfActionable(addResult.error.error);
        return;
      }

      startPromise(onComplete({ addedAccounts: addResult.value, modulesToEnable: payload.modules }));
    }
    else {
      if (options?.wait)
        await accountAdditionService.addMultipleEvmAccounts(payload, onComplete);
      else
        startPromise(accountAdditionService.addMultipleEvmAccounts(payload, onComplete));
    }
  };

  /**
   * An xpub is added as a single unit, so it has no per-account payload to filter against the existing
   * accounts and enables no modules.
   */
  const resolveAdditionPayload = (chain: string, payload: AddAccountsPayload | XpubAccountPayload): {
    filteredPayload: ReturnType<typeof accountAdditionService.getNewAccountPayload>;
    isXpub: boolean;
    modules: AddAccountsPayload['modules'];
  } => {
    if ('xpub' in payload)
      return { filteredPayload: [], isXpub: true, modules: [] };

    return {
      filteredPayload: accountAdditionService.getNewAccountPayload(chain, payload.payload),
      isXpub: false,
      modules: payload.modules,
    };
  };

  const addAccounts = async (chain: string, payload: AddAccountsPayload | XpubAccountPayload, options?: AddAccountsOption): Promise<void> => {
    if (get(addRunning).active) {
      logger.debug('account add is already running.');
      return;
    }

    const { filteredPayload, isXpub, modules } = resolveAdditionPayload(chain, payload);
    if (filteredPayload.length === 0 && !isXpub) {
      const title = t('actions.balances.blockchain_accounts_add.task.title', {
        blockchain: getChainName(chain),
      });
      const message = t('actions.balances.blockchain_accounts_add.no_new.description');
      notifyInfo(title, message);
      return;
    }

    const onComplete = async (params: { addedAccounts: ChainAddress[]; chain: string; isXpub?: boolean; modulesToEnable?: any[] }): Promise<void> =>
      accountAdditionService.completeAccountAddition(params, refreshAccounts, fetchAccounts);

    if (filteredPayload.length === 1 || isXpub) {
      // The `in` check rather than `isXpub`, so `payload` narrows to the xpub variant here.
      const addResult = await accountAdditionService.addSingleAccount('xpub' in payload ? payload : filteredPayload[0], chain);
      if (isErr(addResult)) {
        throwIfActionable(addResult.error.error);
        return;
      }

      startPromise(onComplete({
        addedAccounts: [{ address: addResult.value, chain }],
        chain,
        isXpub,
        modulesToEnable: modules,
      }));
      return;
    }

    const addition = accountAdditionService.addMultipleAccounts(filteredPayload, chain, modules, onComplete);
    // Only an explicit wait blocks the caller; otherwise the additions run in the background.
    if (options?.wait)
      await addition;
    else
      startPromise(addition);
  };

  return {
    addAccounts,
    addEvmAccounts,
    detectEvmAccounts,
    fetchAccounts,
    refreshAccounts,
  };
}
