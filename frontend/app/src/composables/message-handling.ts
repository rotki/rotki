import {
  type Notification,
  type NotificationAction,
  NotificationGroup,
  Priority,
  Severity,
} from '@rotki/common/lib/messages';
import {
  type AccountingRuleConflictData,
  type BalanceSnapshotError,
  type EvmTransactionQueryData,
  type EvmUnDecodedTransactionsData,
  type HistoryEventsQueryData,
  MESSAGE_WARNING,
  type MissingApiKey,
  type NewDetectedToken,
  type PremiumStatusUpdateData,
  SocketMessageType,
  WebsocketMessage,
} from '@/types/websocket-messages';
import { camelCaseTransformer } from '@/services/axios-tranformers';
import { Routes } from '@/router/routes';
import { router } from '@/router';
import type { Blockchain } from '@rotki/common/lib/blockchain';

export function useMessageHandling() {
  const { setQueryStatus: setTxQueryStatus } = useTxQueryStatusStore();
  const { setQueryStatus: setEventsQueryStatus } = useEventsQueryStatusStore();
  const { setUnDecodedTransactionsStatus } = useHistoryStore();
  const { updateDataMigrationStatus, updateDbUpgradeStatus } = useSessionAuthStore();
  const { fetchBlockchainBalances } = useBlockchainBalances();
  const notificationsStore = useNotificationsStore();
  const { data: notifications } = storeToRefs(notificationsStore);
  const { notify } = notificationsStore;
  const { addNewDetectedToken } = useNewlyDetectedTokens();
  const { t } = useI18n();
  const { consumeMessages } = useSessionApi();
  const { uploadStatus, uploadStatusAlreadyHandled } = useSync();
  let isRunning = false;

  const handleSnapshotError = (data: BalanceSnapshotError): Notification => ({
    title: t('notification_messages.snapshot_failed.title'),
    message: t('notification_messages.snapshot_failed.message', data),
    display: true,
  });

  const handleEvmTransactionsStatus = (data: EvmTransactionQueryData): void => {
    setTxQueryStatus(data);
  };

  const handleUnDecodedTransaction = (
    data: EvmUnDecodedTransactionsData,
  ): void => {
    setUnDecodedTransactionsStatus(data);
  };

  const handleHistoryEventsStatus = (data: HistoryEventsQueryData): void => {
    setEventsQueryStatus(data);
  };

  const handleLegacyMessage = (
    message: string,
    isWarning: boolean,
  ): Notification => ({
    title: t('notification_messages.backend.title'),
    message,
    display: !isWarning,
    severity: isWarning ? Severity.WARNING : Severity.ERROR,
    priority: Priority.BULK,
  });

  const handlePremiumStatusUpdate = (
    data: PremiumStatusUpdateData,
  ): Notification | null => {
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
  const { getChainName } = useSupportedChains();

  const handleNewTokenDetectedMessage = (
    data: NewDetectedToken,
  ): Notification | null => {
    const notification = get(notifications).find(
      ({ group }) => group === NotificationGroup.NEW_DETECTED_TOKENS,
    );

    const countAdded = addNewDetectedToken(data);
    const count = (notification?.groupCount || 0) + +countAdded;

    if (count === 0)
      return null;

    return {
      title: t('notification_messages.new_detected_token.title', count),
      message: t(
        'notification_messages.new_detected_token.message',
        {
          identifier: data.tokenIdentifier,
          count,
        },
        count,
      ),
      display: true,
      severity: Severity.INFO,
      priority: Priority.ACTION,
      action: {
        label: t('notification_messages.new_detected_token.action'),
        action: () => router.push(Routes.ASSET_MANAGER_NEWLY_DETECTED),
      },
      group: NotificationGroup.NEW_DETECTED_TOKENS,
      groupCount: count,
    };
  };

  const handleMissingApiKeyMessage = (data: MissingApiKey): Notification => {
    const { service, location } = data;
    const { external, route } = getServiceRegisterUrl(service, location);
    const locationName = get(getChainName(location as Blockchain));

    const actions: NotificationAction[] = [];

    if (route) {
      actions.push({
        label: t('notification_messages.missing_api_key.action'),
        action: () => router.push(route),
        persist: true,
      });
    }

    if (external) {
      const { openUrl } = useInterop();

      actions.push({
        label: t('notification_messages.missing_api_key.get_key'),
        icon: 'external-link-line',
        action: () => openUrl(external),
        persist: true,
      });
    }

    return {
      title: t('notification_messages.missing_api_key.title', {
        service: toHumanReadable(service, 'capitalize'),
        location: toHumanReadable(locationName, 'capitalize'),
      }),
      message: '',
      i18nParam: {
        message: 'notification_messages.missing_api_key.message',
        choice: 0,
        props: {
          service: toHumanReadable(service, 'capitalize'),
          location: toHumanReadable(locationName, 'capitalize'),
          key: location,
          url: external ?? '',
        },
      },
      severity: Severity.WARNING,
      priority: Priority.ACTION,
      action: actions,
    };
  };

  const handleAccountingRuleConflictMessage = (
    data: AccountingRuleConflictData,
  ): Notification => {
    const { numOfConflicts } = data;

    return {
      title: t('notification_messages.accounting_rule_conflict.title'),
      message: t('notification_messages.accounting_rule_conflict.message', {
        conflicts: numOfConflicts,
      }),
      display: true,
      severity: Severity.WARNING,
      priority: Priority.ACTION,
      action: {
        label: t('notification_messages.accounting_rule_conflict.action'),
        action: () =>
          router.push({
            path: Routes.SETTINGS_ACCOUNTING,
            query: { resolveConflicts: 'true' },
          }),
      },
    };
  };

  const handleMessage = async (data: string): Promise<void> => {
    const message: WebsocketMessage = WebsocketMessage.parse(
      camelCaseTransformer(JSON.parse(data)),
    );
    const type = message.type;

    const notifications: Notification[] = [];

    const addNotification = (notification: Notification | null) => {
      if (notification)
        notifications.push(notification);
    };

    if (type === SocketMessageType.MISSING_API_KEY) {
      notifications.push(handleMissingApiKeyMessage(message.data));
    }
    else if (type === SocketMessageType.BALANCES_SNAPSHOT_ERROR) {
      notifications.push(handleSnapshotError(message.data));
    }
    else if (type === SocketMessageType.LEGACY) {
      const data = message.data;
      const isWarning = data.verbosity === MESSAGE_WARNING;
      notifications.push(handleLegacyMessage(data.value, isWarning));
    }
    else if (type === SocketMessageType.EVM_TRANSACTION_STATUS) {
      handleEvmTransactionsStatus(message.data);
    }
    else if (type === SocketMessageType.EVM_UNDECODED_TRANSACTIONS) {
      handleUnDecodedTransaction(message.data);
    }
    else if (type === SocketMessageType.HISTORY_EVENTS_STATUS) {
      handleHistoryEventsStatus(message.data);
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
      addNotification(handleNewTokenDetectedMessage(message.data));
    }
    else if (type === SocketMessageType.REFRESH_BALANCES) {
      await fetchBlockchainBalances({
        blockchain: message.data.blockchain,
        ignoreCache: true,
      });
    }
    else if (type === SocketMessageType.DB_UPLOAD_RESULT) {
      const uploaded = message.data.uploaded;
      if (uploaded) {
        set(uploadStatus, undefined);
        set(uploadStatusAlreadyHandled, false);
      }
      else {
        if (get(uploadStatusAlreadyHandled))
          return;

        set(uploadStatus, message.data);
        set(uploadStatusAlreadyHandled, true);
      }
    }
    else if (type === SocketMessageType.ACCOUNTING_RULE_CONFLICT) {
      notifications.push(handleAccountingRuleConflictMessage(message.data));
    }
    else {
      logger.warn(`Unsupported socket message received: '${type}'`);
    }

    notifications.forEach(notify);
  };

  const handlePollingMessage = (message: string, isWarning: boolean) => {
    const notifications: Notification[] = [];

    try {
      const object = JSON.parse(message);
      if (!object.type)
        notifications.push(handleLegacyMessage(message, isWarning));
      else if (object.type === SocketMessageType.BALANCES_SNAPSHOT_ERROR)
        notifications.push(handleSnapshotError(object));
      else if (object.type === SocketMessageType.EVM_TRANSACTION_STATUS)
        handleEvmTransactionsStatus(object);
      else if (object.type === SocketMessageType.EVM_UNDECODED_TRANSACTIONS)
        handleUnDecodedTransaction(object);
      else if (object.type === SocketMessageType.DB_UPGRADE_STATUS)
        updateDbUpgradeStatus(object);
      else if (object.type === SocketMessageType.DATA_MIGRATION_STATUS)
        updateDataMigrationStatus(object);
      else
        logger.error('unsupported message:', message);
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
        .filter(uniqueStrings)
        .filter(error => !existing.includes(error))
        .forEach(message => handlePollingMessage(message, false));
      messages.warnings
        .filter(uniqueStrings)
        .filter(warning => !existing.includes(warning))
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
