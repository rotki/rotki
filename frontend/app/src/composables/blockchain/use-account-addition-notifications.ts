import { Severity } from '@rotki/common';
import type { EvmAccountsResult } from '@/types/api/accounts';
import type { AccountPayload } from '@/types/blockchain/accounts';

interface NotificationParams { title: string; account: AccountPayload; isAll: boolean; chains: string[] }

interface UseAccountAdditionNotificationsReturn {
  createFailureNotification: (
    failures: Omit<EvmAccountsResult, 'added'>,
    title: string,
    account: AccountPayload
  ) => void;
  notifyUser: ({ title, account, isAll, chains }: NotificationParams) => void;
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

  const notifyUser = ({ title, account, isAll, chains }: NotificationParams): void => {
    notify({
      title,
      message: t('actions.balances.blockchain_accounts_add.success.description', {
        address: account.address,
        list: !isAll ? getChainsText(chains) : '',
      }, isAll ? 1 : 2),
      severity: Severity.INFO,
      display: true,
    });
  };

  function createFailureNotification(
    { noActivity, existed, ethContracts, failed }: Omit<EvmAccountsResult, 'added'>,
    title: string,
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
      title,
      message: t('actions.balances.blockchain_accounts_add.error.failed', {
        address: account.address,
        list: listOfFailureText.join('\n'),
      }),
      display: true,
    });
  }

  return {
    createFailureNotification,
    notifyUser,
  };
}
