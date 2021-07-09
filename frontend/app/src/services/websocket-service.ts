import * as logger from 'loglevel';
import { Severity } from '@/store/notifications/consts';
import { notify } from '@/store/notifications/utils';
import { Nullable } from '@/types';

const MESSAGE_WARNING = 'warning';
const MESSAGE_ERROR = 'error';
const MESSAGE_VERBOSITY = [MESSAGE_WARNING, MESSAGE_ERROR] as const;

export type MessageVerbosity = typeof MESSAGE_VERBOSITY[number];

export interface LegacyMessageData {
  readonly verbosity: MessageVerbosity;
  readonly value: string;
}

const SOCKET_MESSAGE_LEGACY = 'legacy';
const MESSAGE_TYPE = [SOCKET_MESSAGE_LEGACY] as const;
export type SocketMessageType = typeof MESSAGE_TYPE[number];

type MessageData = {
  [SOCKET_MESSAGE_LEGACY]: LegacyMessageData;
};

export interface WebsocketMessage<T extends SocketMessageType> {
  readonly type: T;
  readonly data: MessageData[T];
}

class WebsocketService {
  private _connection: Nullable<WebSocket> = null;

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
      this._connection.onmessage = event => {
        const message: WebsocketMessage<SocketMessageType> = JSON.parse(
          event.data
        );
        if (message.type === SOCKET_MESSAGE_LEGACY) {
          const data = message.data;
          let severity: Severity = Severity.ERROR;
          let display: boolean = true;
          if (data.verbosity === MESSAGE_WARNING) {
            severity = Severity.WARNING;
            display = false;
          }
          notify(data.value, 'Backend', severity, display);
        } else {
          logger.warn(`Unsupported socket message received: ${message}`);
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
