import { type Notification, Priority, Severity } from '@rotki/common';
import {
  type BalanceSnapshotError,
  type DbUploadResult,
  MESSAGE_WARNING,
  type PremiumStatusUpdateData,
  SocketMessageType,
  WebsocketMessage,
} from '@/types/websocket-messages';
import { camelCaseTransformer } from '@/services/axios-tranformers';
import { useMissingApiKeyHandler } from '@/composables/message-handling/missing-api-key';
import {
  useAccountingRuleConflictMessageHandler,
} from '@/composables/message-handling/accounting-rule-conflict-message';
import { useCalendarReminderHandler } from '@/composables/message-handling/calendar-reminder';
import { useCsvImportResultHandler } from '@/composables/message-handling/csv-import-result';
import { useNewTokenDetectedHandler } from '@/composables/message-handling/new-token-detected';
import { useExchangeUnknownAssetHandler } from '@/composables/message-handling/exchange-unknown-asset';

interface UseMessageHandling {
  handleMessage: (data: string) => Promise<void>;
  consume: () => Promise<void>;
}

export function useMessageHandling(): UseMessageHandling {
  const { setQueryStatus: setTxQueryStatus } = useTxQueryStatusStore();
  const { setQueryStatus: setEventsQueryStatus } = useEventsQueryStatusStore();
  const { updateDataMigrationStatus, updateDbUpgradeStatus } = useSessionAuthStore();
  const { fetchBlockchainBalances } = useBlockchainBalances();
  const notificationsStore = useNotificationsStore();
  const { data: notifications } = storeToRefs(notificationsStore);
  const { notify } = notificationsStore;
  const { t } = useI18n();
  const { consumeMessages } = useSessionApi();
  const { uploadStatus, uploadStatusAlreadyHandled } = useSync();
  const { setUndecodedTransactionsStatus, setProtocolCacheStatus } = useHistoryStore();
  const { handle: handleMissingApiKeyMessage } = useMissingApiKeyHandler(t);
  const { handle: handleAccountingRuleConflictMessage } = useAccountingRuleConflictMessageHandler(t);
  const { handle: handleCalendarReminder } = useCalendarReminderHandler(t);
  const { handle: handleCsvImportResult } = useCsvImportResultHandler(t);
  const { handle: handleNewTokenDetectedMessage } = useNewTokenDetectedHandler(t);
  const { handle: handleExchangeUnknownAsset } = useExchangeUnknownAssetHandler(t);

  let isRunning = false;

  const handleSnapshotError = (data: BalanceSnapshotError): Notification => ({
    title: t('notification_messages.snapshot_failed.title'),
    message: t('notification_messages.snapshot_failed.message', data),
    display: true,
  });

  const handleLegacyMessage = (message: string, isWarning: boolean): Notification => ({
    title: t('notification_messages.backend.title'),
    message,
    display: !isWarning,
    severity: isWarning ? Severity.WARNING : Severity.ERROR,
    priority: Priority.BULK,
  });

  const handlePremiumStatusUpdate = (data: PremiumStatusUpdateData): Notification | null => {
    const { isPremiumActive: active, expired } = data;
    const premium = usePremium();
    const isPremium = get(premium);

    set(premium, active);
    if (active && !isPremium) {
      return {
        title: t('notification_messages.premium.active.title'),
        message: t('notification_messages.premium.active.message'),
        display: true,
        severity: Severity.INFO,
      };
    }
    else if (!active && isPremium) {
      return {
        title: t('notification_messages.premium.inactive.title'),
        message: expired
          ? t('notification_messages.premium.inactive.expired_message')
          : t('notification_messages.premium.inactive.network_problem_message'),
        display: true,
        severity: Severity.ERROR,
      };
    }

    return null;
  };

  const { setUpgradedAddresses } = useAccountMigrationStore();

  const refreshBalance = async (blockchain: string): Promise<void> => {
    await fetchBlockchainBalances({
      blockchain,
      ignoreCache: true,
    });
  };

  const handleDbUploadResult = (data: DbUploadResult): void => {
    const uploaded = data.uploaded;
    if (uploaded) {
      set(uploadStatus, undefined);
      set(uploadStatusAlreadyHandled, false);
    }
    else {
      if (get(uploadStatusAlreadyHandled))
        return;

      set(uploadStatus, data);
      set(uploadStatusAlreadyHandled, true);
    }
  };

  const handleMessage = async (data: string): Promise<void> => {
    const message: WebsocketMessage = WebsocketMessage.parse(camelCaseTransformer(JSON.parse(data)));
    const type = message.type;

    const notifications: Notification[] = [];

    const addNotification = (notification: Notification | null): void => {
      if (notification)
        notifications.push(notification);
    };

    if (type === SocketMessageType.MISSING_API_KEY) {
      addNotification(handleMissingApiKeyMessage(message.data));
    }
    else if (type === SocketMessageType.BALANCES_SNAPSHOT_ERROR) {
      addNotification(handleSnapshotError(message.data));
    }
    else if (type === SocketMessageType.LEGACY) {
      const data = message.data;
      const isWarning = data.verbosity === MESSAGE_WARNING;
      addNotification(handleLegacyMessage(data.value, isWarning));
    }
    else if (type === SocketMessageType.EVM_TRANSACTION_STATUS) {
      setTxQueryStatus(message.data);
    }
    else if (type === SocketMessageType.EVM_UNDECODED_TRANSACTIONS) {
      setUndecodedTransactionsStatus(message.data);
    }
    else if (type === SocketMessageType.HISTORY_EVENTS_STATUS) {
      setEventsQueryStatus(message.data);
    }
    else if (type === SocketMessageType.PREMIUM_STATUS_UPDATE) {
      addNotification(handlePremiumStatusUpdate(message.data));
    }
    else if (type === SocketMessageType.DB_UPGRADE_STATUS) {
      updateDbUpgradeStatus(message.data);
    }
    else if (type === SocketMessageType.DATA_MIGRATION_STATUS) {
      updateDataMigrationStatus(message.data);
    }
    else if (type === SocketMessageType.EVM_ACCOUNTS_DETECTION) {
      setUpgradedAddresses(message.data);
    }
    else if (type === SocketMessageType.NEW_EVM_TOKEN_DETECTED) {
      addNotification(handleNewTokenDetectedMessage(message.data, notifications));
    }
    else if (type === SocketMessageType.REFRESH_BALANCES) {
      await refreshBalance(message.data.blockchain);
    }
    else if (type === SocketMessageType.DB_UPLOAD_RESULT) {
      handleDbUploadResult(message.data);
    }
    else if (type === SocketMessageType.ACCOUNTING_RULE_CONFLICT) {
      addNotification(handleAccountingRuleConflictMessage(message.data));
    }
    else if (type === SocketMessageType.CALENDAR_REMINDER) {
      addNotification(handleCalendarReminder(message.data));
    }
    else if (type === SocketMessageType.PROTOCOL_CACHE_UPDATES) {
      setProtocolCacheStatus(message.data);
    }
    else if (type === SocketMessageType.CSV_IMPORT_RESULT) {
      addNotification(handleCsvImportResult(message.data));
    }
    else if (type === SocketMessageType.EXCHANGE_UNKNOWN_ASSET) {
      addNotification(handleExchangeUnknownAsset(message.data));
    }
    else {
      logger.warn(`Unsupported socket message received: '${type}'`);
    }

    notifications.forEach(notify);
  };

  const handlePollingMessage = (message: string, isWarning: boolean): void => {
    const notifications: Notification[] = [];

    try {
      const object = JSON.parse(message);
      if (!object.type)
        notifications.push(handleLegacyMessage(message, isWarning));
      else if (object.type === SocketMessageType.BALANCES_SNAPSHOT_ERROR)
        notifications.push(handleSnapshotError(object));
      else if (object.type === SocketMessageType.EVM_TRANSACTION_STATUS)
        setTxQueryStatus(object);
      else if (object.type === SocketMessageType.EVM_UNDECODED_TRANSACTIONS)
        setUndecodedTransactionsStatus(object);
      else if (object.type === SocketMessageType.DB_UPGRADE_STATUS)
        updateDbUpgradeStatus(object);
      else if (object.type === SocketMessageType.DATA_MIGRATION_STATUS)
        updateDataMigrationStatus(object);
      else logger.error('unsupported message:', message);
    }
    catch {
      notifications.push(handleLegacyMessage(message, isWarning));
    }
    notifications.forEach(notify);
  };

  const consume = async (): Promise<void> => {
    if (isRunning)
      return;

    isRunning = true;
    const title = t('actions.notifications.consume.message_title');

    try {
      const messages = await backoff(3, () => consumeMessages(), 10000);
      const existing = get(notifications).map(({ message }) => message);
      messages.errors
        .filter((error, ...args) => uniqueStrings(error, ...args) && !existing.includes(error))
        .forEach(message => handlePollingMessage(message, false));
      messages.warnings
        .filter((warning, ...args) => uniqueStrings(warning, ...args) && !existing.includes(warning))
        .forEach(message => handlePollingMessage(message, true));
    }
    catch (error: any) {
      const message = error.message || error;
      notify({
        title,
        message,
        display: true,
      });
    }
    finally {
      isRunning = false;
    }
  };

  return {
    handleMessage,
    consume,
  };
}
