import { Severity } from '@rotki/common/lib/messages';
import { get } from '@vueuse/core';
import { getPremium, setPremium } from '@/composables/premium';
import i18n from '@/i18n';
import {
  BalanceSnapshotError,
  EthereumTransactionQueryData,
  PremiumStatusUpdateData,
  SocketMessageType,
  WebsocketMessage
} from '@/services/websocket/messages';
import { useTxQueryStatus } from '@/store/history/query-status';
import { useNotifications } from '@/store/notifications';

export async function handleSnapshotError(
  message: WebsocketMessage<SocketMessageType>
) {
  const data = BalanceSnapshotError.parse(message.data);
  const { notify } = useNotifications();
  notify({
    title: i18n.t('notification_messages.snapshot_failed.title').toString(),
    message: i18n
      .t('notification_messages.snapshot_failed.message', data)
      .toString(),
    display: true
  });
}

export async function handleEthereumTransactionStatus(
  message: WebsocketMessage<SocketMessageType>
) {
  const data = EthereumTransactionQueryData.parse(message.data);
  const { setQueryStatus } = useTxQueryStatus();
  setQueryStatus(data);
}

export async function handleLegacyMessage(message: string, isWarning: boolean) {
  const { notify } = useNotifications();
  notify({
    title: i18n.t('notification_messages.backend.title').toString(),
    message: message,
    display: !isWarning,
    severity: isWarning ? Severity.WARNING : Severity.ERROR
  });
}

export async function handlePremiumStatusUpdate(data: PremiumStatusUpdateData) {
  const { notify } = useNotifications();
  const { is_premium_active: active, expired } = data;
  const isPremium = getPremium();

  if (active && !get(isPremium)) {
    notify({
      title: i18n.t('notification_messages.premium.active.title').toString(),
      message: i18n
        .t('notification_messages.premium.active.message')
        .toString(),
      display: true,
      severity: Severity.INFO
    });
  } else if (!active && get(isPremium)) {
    notify({
      title: i18n.t('notification_messages.premium.inactive.title').toString(),
      message: expired
        ? i18n
            .t('notification_messages.premium.inactive.expired_message')
            .toString()
        : i18n
            .t('notification_messages.premium.inactive.network_problem_message')
            .toString(),
      display: true,
      severity: Severity.ERROR
    });
  }

  setPremium(active);
}
