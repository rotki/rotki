import { Ref } from 'vue';
import { api } from '@/services/rotkehlchen-api';
import { useNotifications } from '@/store/notifications';
import { Nullable } from '@/types';
import {
  LegacyMessageData,
  MESSAGE_WARNING,
  PremiumStatusUpdateData,
  SocketMessageType,
  WebsocketMessage
} from '@/types/websocket-messages';
import { startPromise } from '@/utils';
import { logger } from '@/utils/logging';
import {
  handleEthereumTransactionStatus,
  handleLegacyMessage,
  handlePremiumStatusUpdate,
  handleSnapshotError
} from '@/utils/message-handling';

export const useWebsocketStore = defineStore('websocket', () => {
  const connection: Ref<Nullable<WebSocket>> = ref(null);
  const connected: Ref<boolean> = ref(false);

  const { notify } = useNotifications();
  const { tc } = useI18n();

  const handleMessage = async (event: MessageEvent<any>): Promise<void> => {
    const message: WebsocketMessage<SocketMessageType> = JSON.parse(event.data);
    const type = message.type;

    if (type === SocketMessageType.BALANCES_SNAPSHOT_ERROR) {
      notify(handleSnapshotError(message, tc));
    } else if (type === SocketMessageType.LEGACY) {
      const data = LegacyMessageData.parse(message.data);
      notify(
        handleLegacyMessage(data.value, data.verbosity === MESSAGE_WARNING, tc)
      );
    } else if (type === SocketMessageType.ETHEREUM_TRANSACTION_STATUS) {
      await handleEthereumTransactionStatus(message);
    } else if (type === SocketMessageType.PREMIUM_STATUS_UPDATE) {
      const data = PremiumStatusUpdateData.parse(message.data);
      const notification = handlePremiumStatusUpdate(data, tc);
      if (notification) {
        notify(notification);
      }
    } else {
      logger.warn(`Unsupported socket message received: ${event.data}`);
    }
  };

  const reconnect = async (): Promise<void> => {
    logger.debug('Close was not clean attempting reconnect');
    try {
      await connect();
      logger.debug('websocket reconnection complete');
    } catch (e: any) {
      logger.debug(e, 'Reconnect failed');
    }
  };

  async function connect(): Promise<boolean> {
    return new Promise<boolean>(resolve => {
      const serverUrl = api.serverUrl;
      let protocol = 'ws';
      const location = window.location;
      if (
        serverUrl?.startsWith('https') ||
        location.protocol.startsWith('https')
      ) {
        protocol = 'wss';
      }
      const baseUrl = serverUrl ? serverUrl.split('://')[1] : location.host;

      const url = `${protocol}://${baseUrl}/ws/`;
      logger.debug(`preparing to connect to ${url}`);
      const ws = new WebSocket(url);
      set(connection, ws);
      ws.onmessage = async event => await handleMessage(event);
      ws.onopen = () => {
        logger.debug('websocket connected');
        set(connected, true);
        resolve(true);
      };
      ws.onerror = () => {
        logger.error('websocket connection failed');
        set(connected, false);
        resolve(false);
      };
      ws.onclose = event => {
        logger.debug('websocket connection closed');
        set(connected, false);
        if (!event.wasClean) {
          startPromise(reconnect());
        }
      };
    });
  }

  const disconnect = (): void => {
    const ws = get(connection);
    if (!ws) {
      logger.debug('websocket was not connected');
      return;
    }
    ws.close();
    logger.debug('websocket was disconnected');
  };

  return {
    connected,
    connect,
    disconnect
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useWebsocketStore, import.meta.hot));
}
