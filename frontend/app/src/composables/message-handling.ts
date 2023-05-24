import {
  type Notification,
  NotificationGroup,
  Priority,
  Severity
} from '@rotki/common/lib/messages';
import {
  type BalanceSnapshotError,
  type EvmTransactionQueryData,
  type HistoryEventsQueryData,
  MESSAGE_WARNING,
  type MissingApiKey,
  type NewDetectedToken,
  type PremiumStatusUpdateData,
  SocketMessageType,
  WebsocketMessage
} from '@/types/websocket-messages';
import { camelCaseTransformer } from '@/services/axios-tranformers';
import { Routes } from '@/router/routes';
import router from '@/router';

export const useMessageHandling = () => {
  const { setQueryStatus: setTxQueryStatus } = useTxQueryStatusStore();
  const { setQueryStatus: setEventsQueryStatus } = useEventsQueryStatusStore();
  const { updateDataMigrationStatus, updateDbUpgradeStatus } =
    useSessionAuthStore();
  const { fetchBlockchainBalances } = useBlockchainBalances();
  const notificationsStore = useNotificationsStore();
  const { data: notifications } = storeToRefs(notificationsStore);
  const { notify } = notificationsStore;
  const { addNewDetectedToken } = useNewlyDetectedTokens();
  const { t } = useI18n();
  const { consumeMessages } = useSessionApi();
  let isRunning = false;

  const handleSnapshotError = (data: BalanceSnapshotError): Notification => ({
    title: t('notification_messages.snapshot_failed.title'),
    message: t('notification_messages.snapshot_failed.message', data),
    display: true
  });

  const handleEvmTransactionsStatus = (data: EvmTransactionQueryData): void => {
    setTxQueryStatus(data);
  };

  const handleHistoryEventsStatus = (data: HistoryEventsQueryData): void => {
    setEventsQueryStatus(data);
  };

  const handleLegacyMessage = (
    message: string,
    isWarning: boolean
  ): Notification => ({
    title: t('notification_messages.backend.title'),
    message,
    display: !isWarning,
    severity: isWarning ? Severity.WARNING : Severity.ERROR,
    priority: Priority.BULK
  });

  const handlePremiumStatusUpdate = (
    data: PremiumStatusUpdateData
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
        severity: Severity.INFO
      };
    } else if (!active && isPremium) {
      return {
        title: t('notification_messages.premium.inactive.title'),
        message: expired
          ? t('notification_messages.premium.inactive.expired_message')
          : t('notification_messages.premium.inactive.network_problem_message'),
        display: true,
        severity: Severity.ERROR
      };
    }

    return null;
  };

  const { setUpgradedAddresses } = useAccountMigrationStore();

  const handleNewTokenDetectedMessage = (
    data: NewDetectedToken
  ): Notification => {
    const notification = get(notifications).find(
      ({ group }) => group === NotificationGroup.NEW_DETECTED_TOKENS
    );

    addNewDetectedToken(data);

    const count = (notification?.groupCount || 0) + 1;

    return {
      title: t('notification_messages.new_detected_token.title', count),
      message: t(
        'notification_messages.new_detected_token.message',
        {
          identifier: data.tokenIdentifier,
          count
        },
        count
      ),
      display: true,
      severity: Severity.INFO,
      priority: Priority.ACTION,
      action: {
        label: t('notification_messages.new_detected_token.action'),
        action: () => router.push(Routes.ASSET_MANAGER_NEWLY_DETECTED)
      },
      group: NotificationGroup.NEW_DETECTED_TOKENS,
      groupCount: count
    };
  };

  const handleMissingApiKeyMessage = (data: MissingApiKey): Notification => {
    const { service, location } = data;
    const { external, route } = getServiceRegisterUrl(service, location);

    return {
      title: t('notification_messages.missing_api_key.title', {
        service: toSentenceCase(service),
        location: toSentenceCase(location)
      }),
      message: '',
      i18nParam: {
        message: 'notification_messages.missing_api_key.message',
        choice: 0,
        props: {
          service: toSentenceCase(service),
          location: toSentenceCase(location),
          url: external ?? ''
        }
      },
      severity: Severity.WARNING,
      priority: Priority.ACTION,
      action: !route
        ? undefined
        : {
            label: t('notification_messages.missing_api_key.action'),
            action: () => router.push(route)
          }
    };
  };

  const handleMessage = async (data: string): Promise<void> => {
    const message: WebsocketMessage = WebsocketMessage.parse(
      camelCaseTransformer(JSON.parse(data))
    );
    const type = message.type;

    const notifications: Notification[] = [];

    if (type === SocketMessageType.MISSING_API_KEY) {
      notifications.push(handleMissingApiKeyMessage(message.data));
    } else if (type === SocketMessageType.BALANCES_SNAPSHOT_ERROR) {
      notifications.push(handleSnapshotError(message.data));
    } else if (type === SocketMessageType.LEGACY) {
      const data = message.data;
      const isWarning = data.verbosity === MESSAGE_WARNING;
      notifications.push(handleLegacyMessage(data.value, isWarning));
    } else if (type === SocketMessageType.EVM_TRANSACTION_STATUS) {
      handleEvmTransactionsStatus(message.data);
    } else if (type === SocketMessageType.HISTORY_EVENTS_STATUS) {
      handleHistoryEventsStatus(message.data);
    } else if (type === SocketMessageType.PREMIUM_STATUS_UPDATE) {
      const notification = handlePremiumStatusUpdate(message.data);
      if (notification) {
        notifications.push(notification);
      }
    } else if (type === SocketMessageType.DB_UPGRADE_STATUS) {
      updateDbUpgradeStatus(message.data);
    } else if (type === SocketMessageType.DATA_MIGRATION_STATUS) {
      updateDataMigrationStatus(message.data);
    } else if (type === SocketMessageType.EVM_ACCOUNTS_DETECTION) {
      setUpgradedAddresses(message.data);
    } else if (type === SocketMessageType.NEW_EVM_TOKEN_DETECTED) {
      notifications.push(handleNewTokenDetectedMessage(message.data));
    } else if (type === SocketMessageType.REFRESH_BALANCES) {
      await fetchBlockchainBalances({
        blockchain: message.data.blockchain,
        ignoreCache: true
      });
    } else {
      logger.warn(`Unsupported socket message received: '${type}'`);
    }

    notifications.forEach(notify);
  };

  const handlePollingMessage = async (message: string, isWarning: boolean) => {
    const notifications: Notification[] = [];

    try {
      const object = JSON.parse(message);
      if (!object.type) {
        notifications.push(handleLegacyMessage(message, isWarning));
      } else if (object.type === SocketMessageType.BALANCES_SNAPSHOT_ERROR) {
        notifications.push(handleSnapshotError(object));
      } else if (object.type === SocketMessageType.EVM_TRANSACTION_STATUS) {
        await handleEvmTransactionsStatus(object);
      } else if (object.type === SocketMessageType.DB_UPGRADE_STATUS) {
        await updateDbUpgradeStatus(object);
      } else if (object.type === SocketMessageType.DATA_MIGRATION_STATUS) {
        await updateDataMigrationStatus(object);
      } else {
        logger.error('unsupported message:', message);
      }
    } catch {
      notifications.push(handleLegacyMessage(message, isWarning));
    }
    notifications.forEach(notify);
  };

  const consume = async (): Promise<void> => {
    if (isRunning) {
      return;
    }

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
    } catch (e: any) {
      const message = e.message || e;
      notify({
        title,
        message,
        display: true
      });
    } finally {
      isRunning = false;
    }
  };

  return {
    handleMessage,
    consume
  };
};
