import type { DialogEventHandlers } from '@/components/history/events/dialog-types';
import type { RepullingTransactionResult } from '@/composables/history/events/tx';
import type { RefreshTransactionsParams } from '@/composables/history/events/tx/types';
import type { Exchange } from '@/modules/balances/types/exchanges';
import type { LocationAndTxRef, PullLocationTransactionPayload } from '@/modules/history/events/event-payloads';
import { type NotificationAction, Severity } from '@rotki/common';
import { useDecodingStatusStore } from '@/modules/history/use-decoding-status-store';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { Routes } from '@/router/routes';

interface UseHistoryEventsDialogHandlersDeps {
  /** Fetches event data and refreshes associated locations/labels. */
  fetchDataAndLocations: () => Promise<void>;
  /** Forces EVM transaction redecoding for the given payload. */
  forceRedecodeEvmEvents: (data: PullLocationTransactionPayload) => Promise<void>;
  /** Checks missing events and triggers redecoding with confirmation dialog. */
  redecodeAllEvents: () => void;
  /** Refreshes transactions with the given parameters. */
  refreshTransactions: (params?: RefreshTransactionsParams) => Promise<void>;
  /** Checks for missing events and redecodes them. */
  checkMissingEventsAndRedecode: () => Promise<void>;
}

export function useHistoryEventsDialogHandlers(deps: UseHistoryEventsDialogHandlersDeps): DialogEventHandlers {
  const { checkMissingEventsAndRedecode, fetchDataAndLocations, forceRedecodeEvmEvents, redecodeAllEvents, refreshTransactions } = deps;

  const { t } = useI18n({ useScope: 'global' });
  const router = useRouter();
  const { notify } = useNotifications();
  const { resetUndecodedTransactionsStatus } = useDecodingStatusStore();

  const handleTransactionRedecode = async (txRef: LocationAndTxRef): Promise<void> => {
    await forceRedecodeEvmEvents({ transactions: [txRef] });
  };

  return {
    onHistoryEventSaved: fetchDataAndLocations,
    onRedecodeAllEvents: redecodeAllEvents,
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
              path: Routes.HISTORY_EVENTS.toString(),
              query: { txRefs: allTxHashes },
            });
          },
          label: t('actions.repulling_transaction.success.action'),
        };
      }

      notify({
        action,
        display: true,
        message: newTransactionsCount ? t('actions.repulling_transaction.success.description', { length: newTransactionsCount }) : t('actions.repulling_transaction.success.no_tx_description'),
        severity: Severity.INFO,
        title: t('actions.repulling_transaction.task.title'),
      });
    },
    onResetUndecodedTransactions: (): void => {
      resetUndecodedTransactionsStatus();
    },
    onTransactionAdded: handleTransactionRedecode,
  };
}
