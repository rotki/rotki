import * as logger from 'loglevel';
import {
  handleEthereumTransactionStatus,
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
  private readonly pathname: string;

  constructor() {
    const pathname = window.location.pathname;
    this.pathname = pathname.endsWith('/') ? pathname.slice(0, -1) : pathname;
  }

  get connected(): boolean {
    return false;
  }

  connect(): Promise<boolean> {
    return new Promise<boolean>(resolve => {
      let websocketUrl = window.interop?.websocketUrl() ?? null;
      const protocol = location.protocol.startsWith('https') ? 'wss' : 'ws';
      if (!websocketUrl) {
        const websocketPort = process.env.VITE_WEBSOCKET_PORT;
        const host = window.location.host;
        if (websocketPort) {
          websocketUrl = `${host.split(':')[0]}:${websocketPort}`;
        } else {
          websocketUrl = `${host}${this.pathname}/ws/`;
        }
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
        } else if (
          message.type === SocketMessageType.ETHEREUM_TRANSACTION_STATUS
        ) {
          await handleEthereumTransactionStatus(message);
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
