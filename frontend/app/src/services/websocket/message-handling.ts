import { SemiPartial } from '@rotki/common';
import { NotificationPayload, Severity } from '@rotki/common/lib/messages';
import { get } from '@vueuse/core';
import { useI18n } from 'vue-i18n-composable';
import { usePremium } from '@/composables/premium';
import {
  BalanceSnapshotError,
  EthereumTransactionQueryData,
  PremiumStatusUpdateData,
  SocketMessageType,
  WebsocketMessage
} from '@/services/websocket/messages';
import { useTxQueryStatus } from '@/store/history/query-status';

export const handleSnapshotError = (
  message: WebsocketMessage<SocketMessageType>
): SemiPartial<NotificationPayload, 'title' | 'message'> => {
  const { tc } = useI18n();
  const data = BalanceSnapshotError.parse(message.data);
  return {
    title: tc('notification_messages.snapshot_failed.title'),
    message: tc('notification_messages.snapshot_failed.message', 0, data),
    display: true
  };
};

export const handleEthereumTransactionStatus = (
  message: WebsocketMessage<SocketMessageType>
) => {
  const data = EthereumTransactionQueryData.parse(message.data);
  const { setQueryStatus } = useTxQueryStatus();
  setQueryStatus(data);
};

export const handleLegacyMessage = (
  message: string,
  isWarning: boolean
): SemiPartial<NotificationPayload, 'title' | 'message'> => {
  const { tc } = useI18n();
  return {
    title: tc('notification_messages.backend.title'),
    message: message,
    display: !isWarning,
    severity: isWarning ? Severity.WARNING : Severity.ERROR
  };
};

export const handlePremiumStatusUpdate = (
  data: PremiumStatusUpdateData
): SemiPartial<NotificationPayload, 'title' | 'message'> | null => {
  const { is_premium_active: active, expired } = data;
  const premium = usePremium();
  const isPremium = get(premium);
  const { tc } = useI18n();

  set(premium, active);
  if (active && !isPremium) {
    return {
      title: tc('notification_messages.premium.active.title'),
      message: tc('notification_messages.premium.active.message'),
      display: true,
      severity: Severity.INFO
    };
  } else if (!active && isPremium) {
    return {
      title: tc('notification_messages.premium.inactive.title'),
      message: expired
        ? tc('notification_messages.premium.inactive.expired_message')
        : tc('notification_messages.premium.inactive.network_problem_message'),
      display: true,
      severity: Severity.ERROR
    };
  }

  return null;
};
