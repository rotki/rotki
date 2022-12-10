import { type SemiPartial } from '@rotki/common';
import { type NotificationPayload, Severity } from '@rotki/common/lib/messages';
import { usePremium } from '@/composables/premium';
import { convertKeys } from '@/services/axios-tranformers';
import { useTxQueryStatus } from '@/store/history/query-status';
import { useSessionAuthStore } from '@/store/session/auth';
import {
  BalanceSnapshotError,
  EthereumTransactionQueryData,
  LoginStatusData,
  type PremiumStatusUpdateData,
  type SocketMessageType,
  type WebsocketMessage
} from '@/types/websocket-messages';
import type VueI18n from 'vue-i18n';

export const handleSnapshotError = (
  message: WebsocketMessage<SocketMessageType>,
  tc: typeof VueI18n.prototype.tc
): SemiPartial<NotificationPayload, 'title' | 'message'> => {
  const data = BalanceSnapshotError.parse(message.data);
  return {
    title: tc('notification_messages.snapshot_failed.title'),
    message: tc('notification_messages.snapshot_failed.message', 0, data),
    display: true
  };
};

export const handleEthereumTransactionStatus = (
  message: WebsocketMessage<SocketMessageType>
): void => {
  const data = EthereumTransactionQueryData.parse(message.data);
  const { setQueryStatus } = useTxQueryStatus();
  setQueryStatus(data);
};

export const handleLegacyMessage = (
  message: string,
  isWarning: boolean,
  tc: typeof VueI18n.prototype.tc
): SemiPartial<NotificationPayload, 'title' | 'message'> => {
  return {
    title: tc('notification_messages.backend.title'),
    message,
    display: !isWarning,
    severity: isWarning ? Severity.WARNING : Severity.ERROR
  };
};

export const handlePremiumStatusUpdate = (
  data: PremiumStatusUpdateData,
  tc: typeof VueI18n.prototype.tc
): SemiPartial<NotificationPayload, 'title' | 'message'> | null => {
  const { isPremiumActive: active, expired } = data;
  const premium = usePremium();
  const isPremium = get(premium);

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

export const handleLoginStatus = (
  message: WebsocketMessage<SocketMessageType>
): void => {
  const { handleLoginStatus } = useSessionAuthStore();
  const data = LoginStatusData.parse(convertKeys(message.data, true, false));
  handleLoginStatus(data);
};
