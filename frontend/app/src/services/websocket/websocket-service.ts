import * as logger from 'loglevel';
import {
  handleLegacyMessage,
  handleSnapshotError
} from '@/services/websocket/message-handling';
import {
  LegacyMessageData,
  MESSAGE_WARNING,
  SocketMessageType,
  WebsocketMessage
} from '@/services/websocket/messages';
import { Nullable } from '@/types';

class WebsocketService {
  private _connection: Nullable<WebSocket> = null;
  private _connected: boolean = false;

  get connected(): boolean {
    return false;
  }

  connect(): Promise<boolean> {
    return new Promise<boolean>(resolve => {
      let websocketUrl = window.interop?.websocketUrl() ?? null;
      const protocol = location.protocol.startsWith('https') ? 'wss' : 'ws';
      if (!websocketUrl) {
        websocketUrl = `${window.location.host}/ws/`;
      }
      const url = `${protocol}://${websocketUrl}`;
      logger.debug(`preparing to connect to ${url}`);
      this._connection = new WebSocket(url);
      this._connection.onmessage = async event => {
        const message: WebsocketMessage<SocketMessageType> = JSON.parse(
          event.data
        );

        if (message.type === SocketMessageType.BALANCES_SNAPSHOT_ERROR) {
          await handleSnapshotError(message);
        } else if (message.type === SocketMessageType.LEGACY) {
          const data = LegacyMessageData.parse(message.data);
          await handleLegacyMessage(
            data.value,
            data.verbosity === MESSAGE_WARNING
          );
        } else {
          logger.warn(`Unsupported socket message received: ${message}`);
        }
      };
      this._connection.onopen = () => {
        logger.debug('websocket connected');
        this._connected = true;
        resolve(true);
      };
      this._connection.onerror = () => {
        logger.error('websocket connection failed');
        this._connected = false;
        resolve(false);
      };
      this._connection.onclose = event => {
        this._connected = false;
        logger.debug('websocket connection closed');
        if (!event.wasClean) {
          logger.debug('Close was not clean attempting reconnect');
          this.connect().then();
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
