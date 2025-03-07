import type { EvmAccountsResult } from '@/types/api/accounts';
import type { AccountPayload } from '@/types/blockchain/accounts';
import { useSupportedChains } from '@/composables/info/chains';
import { useNotificationsStore } from '@/store/notifications';
import { Severity } from '@rotki/common';

interface NotificationParams { account: AccountPayload; isAll: boolean; chains: string[] }

interface UseAccountAdditionNotificationsReturn {
  createFailureNotification: (
    failures: Omit<EvmAccountsResult, 'added'>,
    account: AccountPayload
  ) => void;
  notifyUser: (params: NotificationParams) => void;
  notifyFailedToAddAddress: (accounts: AccountPayload[], address: number, blockchain?: string) => void;
}

export function useAccountAdditionNotifications(): UseAccountAdditionNotificationsReturn {
  const { t } = useI18n();
  const { notify } = useNotificationsStore();
  const { getChainName } = useSupportedChains();

  const getChainsText = (chains: string[], explanation?: string): string => chains.map((chain) => {
    let text = `- ${get(getChainName(chain))}`;
    if (explanation)
      text += ` (${explanation})`;

    return text;
  }).join('\n');

  const notifyUser = ({ account, chains, isAll }: NotificationParams): void => {
    notify({
      display: true,
      message: t('actions.balances.blockchain_accounts_add.success.description', {
        address: account.address,
        list: !isAll ? getChainsText(chains) : '',
      }, isAll ? 1 : 2),
      severity: Severity.INFO,
      title: t('actions.balances.blockchain_accounts_add.task.title', { blockchain: 'EVM' }),
    });
  };

  const notifyFailedToAddAddress = (accounts: AccountPayload[], address: number, blockchain: string = 'EVM'): void => {
    const title = t('actions.balances.blockchain_accounts_add.task.title', { blockchain: blockchain === 'EVM' ? blockchain : get(getChainName(blockchain)) });
    const message = t('actions.balances.blockchain_accounts_add.error.failed_list_description', {
      address,
      blockchain,
      list: accounts.map(({ address }) => `- ${address}`).join('\n'),
    });

    notify({
      display: true,
      message,
      title,
    });
  };

  function createFailureNotification(
    { ethContracts, existed, failed, noActivity }: Omit<EvmAccountsResult, 'added'>,
    account: AccountPayload,
  ): void {
    const listOfFailureText: string[] = [];

    const addFailureMessage = (value?: Record<string, string[]>, reason?: string): void => {
      if (!value)
        return;

      listOfFailureText.push(getChainsText(Object.values(value)[0], reason));
    };

    addFailureMessage(noActivity, t('actions.balances.blockchain_accounts_add.error.failed_reason.no_activity'));
    addFailureMessage(existed, t('actions.balances.blockchain_accounts_add.error.failed_reason.existed'));
    addFailureMessage(ethContracts ? { ethContracts: [t('actions.balances.blockchain_accounts_add.error.non_eth')] } : undefined, t('actions.balances.blockchain_accounts_add.error.failed_reason.is_contract'));
    addFailureMessage(failed);

    if (listOfFailureText.length <= 0)
      return;

    notify({
      display: true,
      message: t('actions.balances.blockchain_accounts_add.error.failed', {
        address: account.address,
        list: listOfFailureText.join('\n'),
      }),
      severity: Severity.WARNING,
      title: t('actions.balances.blockchain_accounts_add.task.title', { blockchain: 'EVM' }),
    });
  }

  return {
    createFailureNotification,
    notifyFailedToAddAddress,
    notifyUser,
  };
}
