import * as logger from 'loglevel';
import { api } from '@/services/rotkehlchen-api';
import {
  handleEthereumTransactionStatus,
  handleLegacyMessage,
  handlePremiumStatusUpdate,
  handleSnapshotError
} from '@/services/websocket/message-handling';
import {
  LegacyMessageData,
  MESSAGE_WARNING,
  PremiumStatusUpdateData,
  SocketMessageType,
  WebsocketMessage
} from '@/services/websocket/messages';
import { useNotifications } from '@/store/notifications';
import { Nullable } from '@/types';

class WebsocketService {
  private _connection: Nullable<WebSocket> = null;

  get connected(): boolean {
    return false;
  }

  connect(): Promise<boolean> {
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
      this._connection = new WebSocket(url);
      this._connection.onmessage = async event => {
        const { notify } = useNotifications();
        const message: WebsocketMessage<SocketMessageType> = JSON.parse(
          event.data
        );

        if (message.type === SocketMessageType.BALANCES_SNAPSHOT_ERROR) {
          notify(handleSnapshotError(message));
        } else if (message.type === SocketMessageType.LEGACY) {
          const data = LegacyMessageData.parse(message.data);
          notify(
            handleLegacyMessage(data.value, data.verbosity === MESSAGE_WARNING)
          );
        } else if (
          message.type === SocketMessageType.ETHEREUM_TRANSACTION_STATUS
        ) {
          await handleEthereumTransactionStatus(message);
        } else if (message.type === SocketMessageType.PREMIUM_STATUS_UPDATE) {
          const data = PremiumStatusUpdateData.parse(message.data);
          const notification = handlePremiumStatusUpdate(data);
          if (notification) {
            notify(notification);
          }
        } else {
          logger.warn(`Unsupported socket message received: ${event.data}`);
        }
      };
      this._connection.onopen = () => {
        logger.debug('websocket connected');
        resolve(true);
      };
      this._connection.onerror = () => {
        logger.error('websocket connection failed');
        resolve(false);
      };
      this._connection.onclose = event => {
        logger.debug('websocket connection closed');
        if (!event.wasClean) {
          logger.debug('Close was not clean attempting reconnect');
          this.connect()
            .then(() => {
              logger.debug('websocket reconnection complete');
            })
            .catch(e => logger.debug(e, 'Reconnect failed'));
        }
      };
    });
  }

  disconnect() {
    this._connection?.close();
    logger.debug('websocket was disconnected');
  }
}

export const websocket = new WebsocketService();
