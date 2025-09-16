import { useRefresh } from '@/composables/balances/refresh';
import { useConfirmStore } from '@/store/confirm';

interface AccountBalancesTokenDetectionReturn {
  redetectAllClicked: () => void;
}

export function useAccountBalancesTokenDetection(): AccountBalancesTokenDetectionReturn {
  const { t } = useI18n();
  const { show } = useConfirmStore();
  const { handleBlockchainRefresh } = useRefresh();

  const redetectAllClicked = (): void => {
    show({
      message: t('account_balances.detect_tokens.confirmation.message'),
      title: t('account_balances.detect_tokens.confirmation.title'),
      type: 'info',
    }, async () => {
      await handleBlockchainRefresh(undefined, true);
    });
  };

  return {
    redetectAllClicked,
  };
}
