import type { Exchange } from '@/modules/balances/types/exchanges';
import type { DialogEventHandlers } from '@/modules/history/events/dialog-types';
import type { LocationAndTxRef, PullLocationTransactionPayload } from '@/modules/history/events/event-payloads';
import type { RefreshTransactionsParams } from '@/modules/history/events/tx/types';
import type { RepullingTransactionResult } from '@/modules/history/events/tx/use-history-transactions';
import { type NotificationAction, NotificationKind, Severity } from '@rotki/common';
import { useNotifications } from '@/modules/core/notifications/use-notifications';

interface UseHistoryEventsDialogHandlersDeps {
  /** Fetches event data and refreshes associated locations/labels. */
  fetchDataAndLocations: () => Promise<void>;
  /** Forces EVM transaction redecoding for the given payload. */
  forceRedecodeEvmEvents: (data: PullLocationTransactionPayload) => Promise<void>;
  /** Refreshes transactions with the given parameters. */
  refreshTransactions: (params?: RefreshTransactionsParams) => Promise<void>;
  /** Checks for missing events and redecodes them. */
  checkMissingEventsAndRedecode: () => Promise<void>;
}

export function useHistoryEventsDialogHandlers(deps: UseHistoryEventsDialogHandlersDeps): DialogEventHandlers {
  const { checkMissingEventsAndRedecode, fetchDataAndLocations, forceRedecodeEvmEvents, refreshTransactions } = deps;

  const { t } = useI18n({ useScope: 'global' });
  const router = useRouter();
  const { notify } = useNotifications();

  const handleTransactionRedecode = async (txRef: LocationAndTxRef): Promise<void> => {
    await forceRedecodeEvmEvents({ transactions: [txRef] });
  };

  return {
    onHistoryEventSaved: fetchDataAndLocations,
    onRedecodeTransaction: handleTransactionRedecode,
    onRepullExchangeEvents: async (exchanges: Exchange[]): Promise<void> => {
      await refreshTransactions({
        disableEvmEvents: true,
        payload: {
          exchanges,
        },
        userInitiated: true,
      });
    },
    onRepullTransactions: async (result: RepullingTransactionResult): Promise<void> => {
      await checkMissingEventsAndRedecode();

      const { newTransactions, newTransactionsCount } = result;

      let action: NotificationAction | undefined;
      if (newTransactionsCount > 0) {
        const allTxHashes = Object.values(newTransactions).flat();
        action = {
          action: async (): Promise<void> => {
            await router.push({
              name: '/history/events/',
              query: { txRefs: allTxHashes },
            });
          },
          label: t('actions.repulling_transaction.success.action'),
        };
      }

      notify({
        action,
        message: newTransactionsCount ? t('actions.repulling_transaction.success.description', { length: newTransactionsCount }) : t('actions.repulling_transaction.success.no_tx_description'),
        kind: NotificationKind.RESULT,
        severity: Severity.INFO,
        title: t('actions.repulling_transaction.task.title'),
      });
    },
    onTransactionAdded: handleTransactionRedecode,
  };
}
