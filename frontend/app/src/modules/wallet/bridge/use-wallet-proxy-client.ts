import { BRIDGE_NOTIFICATION_TYPES } from '@shared/proxy/constants';
import {
  isWalletBridgeNotification,
  isWalletBridgeRequest,
  parseWalletBridgeMessage,
  type WalletBridgeMessage,
  type WalletBridgeNotification,
  type WalletBridgeParseError,
  type WalletBridgeRequest,
  type WalletBridgeResponse,
} from '@shared/wallet-bridge-types';
import { defaultWindow, get, isDefined, set } from '@vueuse/core';
import { ref, type Ref } from 'vue';
import { logger } from '@/modules/core/common/logging/logging';
import { useBridgeMessageHandlers } from '@/modules/wallet/bridge/use-bridge-message-handlers';
import { CLIENT_CONFIG } from './bridge-config';

/**
 * Lifecycle of the bridge page's socket to the Electron app.
 *
 * @remarks
 * `retriesExhausted`, `takenOver` and `disconnected` are resting phases: nothing leaves them except
 * an explicit `connect()`. `takenOver` means another bridge page replaced this one, so reconnecting
 * on our own would steal the connection back.
 */
export const BridgeConnectionPhase = {
  disconnected: 'disconnected',
  connecting: 'connecting',
  connected: 'connected',
  retryWaiting: 'retry-waiting',
  retriesExhausted: 'retries-exhausted',
  takenOver: 'taken-over',
} as const;

/** `attempt` is zero-based and counts consecutive failures since the last successful open. */
export type BridgeConnectionState =
  | { phase: typeof BridgeConnectionPhase.disconnected }
  | { phase: typeof BridgeConnectionPhase.connecting; attempt: number }
  | { phase: typeof BridgeConnectionPhase.connected }
  | { phase: typeof BridgeConnectionPhase.retryWaiting; attempt: number }
  | { phase: typeof BridgeConnectionPhase.retriesExhausted }
  | { phase: typeof BridgeConnectionPhase.takenOver };

interface WalletProxyClientComposable {
  cleanup: () => void;
  connect: () => void;
  disconnect: () => void;
  isConnected: Readonly<Ref<boolean>>;
  isConnecting: Readonly<Ref<boolean>>;
  lastError: Readonly<Ref<string | undefined>>;
  onTakeOver: (callback: () => void) => void;
  state: Readonly<Ref<BridgeConnectionState>>;
}

export function useWalletProxyClient(): WalletProxyClientComposable {
  const state = shallowRef<BridgeConnectionState>({ phase: BridgeConnectionPhase.disconnected });
  const lastError = ref<string>();
  const onTakeOverCallback = ref<() => void>();

  /** The socket of the current generation, assigned at creation so a handshake can be cancelled. */
  let socket: WebSocket | undefined;
  /** Bumped whenever a socket is superseded; callbacks from an older generation are ignored. */
  let generation = 0;
  let retryTimeout: ReturnType<typeof setTimeout> | undefined;
  let handshakeTimeout: ReturnType<typeof setTimeout> | undefined;

  const isConnected = computed<boolean>(() => get(state).phase === BridgeConnectionPhase.connected);
  const isConnecting = computed<boolean>(() => get(state).phase === BridgeConnectionPhase.connecting);

  const { handleRequest } = useBridgeMessageHandlers(sendMessage);

  const sendResponse = (response: WalletBridgeResponse): void => {
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(response));
    }
    else {
      logger.error('Cannot send response: WebSocket not connected');
    }
  };

  function handleBridgeNotification(notification: WalletBridgeNotification): void {
    if (notification.type === BRIDGE_NOTIFICATION_TYPES.CLOSE_TAB) {
      logger.info('Received close_tab notification, attempting to close browser tab');
      try {
        defaultWindow?.close();
      }
      catch (error) {
        logger.error('Failed to close tab:', error);
      }
    }
    else if (notification.type === BRIDGE_NOTIFICATION_TYPES.RECONNECTED) {
      logger.info('Received reconnected notification, preventing automatic reconnection');
      cancelRetry();
      set(state, { phase: BridgeConnectionPhase.takenOver });
      if (isDefined(onTakeOverCallback)) {
        get(onTakeOverCallback)();
      }
    }
  }

  function handleWalletBridgeRequest(message: WalletBridgeRequest): void {
    handleRequest(message).then((response) => {
      sendResponse(response);
    }).catch((error) => {
      sendResponse({
        error: {
          code: -32601,
          message: error.message ?? 'Internal error',
        },
        id: message.id,
        jsonrpc: '2.0',
      });
    });
  }

  function dispatchMessage(message: WalletBridgeMessage): void {
    logger.debug('Received WebSocket message:', message);

    if (isWalletBridgeNotification(message))
      handleBridgeNotification(message);
    else if (isWalletBridgeRequest(message))
      handleWalletBridgeRequest(message);
  }

  /**
   * Reports a frame that could not be parsed.
   *
   * @remarks
   * The sender only gets an answer when the frame decoded far enough to show an `id`, since an
   * answer without one could not be matched to anything.
   */
  function rejectMessage(error: WalletBridgeParseError): void {
    logger.error(`Failed to handle WebSocket message (${error.kind}):`, error.cause);
    if (error.kind !== 'invalid-message' || !(typeof error.raw === 'object' && error.raw && 'id' in error.raw))
      return;
    sendResponse({
      error: {
        code: -32700,
        message: 'Parse error',
      },
      id: String(error.raw.id),
      jsonrpc: '2.0',
    });
  }

  const getWebSocketUrl = (): string => {
    const currentPort = defaultWindow?.location.port;
    if (currentPort) {
      // WebSocket server runs on HTTP port + 1
      const wsPort = Number.parseInt(currentPort) + 1;
      return `ws://localhost:${wsPort}/wallet-bridge`;
    }

    // Fallback to default if no port in URL (shouldn't happen for wallet bridge)
    return `ws://localhost:${CLIENT_CONFIG.DEFAULT_BASE_PORT}/wallet-bridge`;
  };

  function cancelRetry(): void {
    clearTimeout(retryTimeout);
    retryTimeout = undefined;
  }

  /** Abandons the current socket, if any, so none of its late callbacks can change state. */
  function supersedeSocket(): void {
    clearTimeout(handshakeTimeout);
    generation++;
    const previous = socket;
    socket = undefined;
    previous?.close();
  }

  /**
   * Moves on from failed attempt `attempt`: either waits and opens the next one, or gives up.
   *
   * @remarks
   * Any timer already pending is cleared first, so two failure reports for one attempt can never
   * leave two retries running.
   */
  function scheduleRetry(attempt: number): void {
    cancelRetry();
    const nextAttempt = attempt + 1;
    if (nextAttempt >= CLIENT_CONFIG.MAX_RETRIES) {
      logger.error('Max WebSocket connection attempts reached');
      set(state, { phase: BridgeConnectionPhase.retriesExhausted });
      return;
    }
    set(state, { attempt: nextAttempt, phase: BridgeConnectionPhase.retryWaiting });
    retryTimeout = setTimeout(() => {
      retryTimeout = undefined;
      openSocket(nextAttempt);
    }, CLIENT_CONFIG.RETRY_DELAY);
  }

  /** A connection that dropped after opening starts a fresh retry budget. */
  function failedAttempt(current: BridgeConnectionState): number {
    return current.phase === BridgeConnectionPhase.connecting ? current.attempt : 0;
  }

  function handleClose(): void {
    clearTimeout(handshakeTimeout);
    socket = undefined;
    const current = get(state);
    logger.info('WebSocket disconnected');
    if (current.phase === BridgeConnectionPhase.takenOver)
      return;
    scheduleRetry(failedAttempt(current));
  }

  /**
   * Records an error without acting on it.
   *
   * @remarks
   * A WebSocket always fires `close` after `error`, so retrying is left to the close handler.
   */
  function handleError(attempt: number, error: unknown): void {
    const errorMessage = `WebSocket connection error (attempt ${attempt + 1}/${CLIENT_CONFIG.MAX_RETRIES})`;
    logger.error(errorMessage, error);
    set(lastError, errorMessage);
  }

  /**
   * Fails an attempt whose handshake never finished.
   *
   * @remarks
   * Not every failure produces an event: a port answered by something that accepts the upgrade and
   * never replies leaves the socket opening forever, with the connect button disabled.
   */
  function handleHandshakeTimeout(attempt: number): void {
    const errorMessage = `WebSocket connection timed out (attempt ${attempt + 1}/${CLIENT_CONFIG.MAX_RETRIES})`;
    logger.error(errorMessage);
    set(lastError, errorMessage);
    supersedeSocket();
    scheduleRetry(attempt);
  }

  function openSocket(attempt: number): void {
    supersedeSocket();
    cancelRetry();
    const socketGeneration = generation;
    const isCurrent = (): boolean => socketGeneration === generation;
    set(state, { attempt, phase: BridgeConnectionPhase.connecting });

    try {
      const wsUrl = getWebSocketUrl();
      logger.info(`Attempting to connect to WebSocket: ${wsUrl}`);
      const websocket = new WebSocket(wsUrl);
      socket = websocket;
      handshakeTimeout = setTimeout(handleHandshakeTimeout, CLIENT_CONFIG.HANDSHAKE_TIMEOUT, attempt);

      websocket.onopen = (): void => {
        if (!isCurrent())
          return;
        clearTimeout(handshakeTimeout);
        set(state, { phase: BridgeConnectionPhase.connected });
        set(lastError, undefined);
        logger.info('WebSocket connected to rotki app');
      };

      websocket.onmessage = (event): void => {
        if (!isCurrent())
          return;
        const parsed = parseWalletBridgeMessage(event.data);
        if (parsed.ok)
          dispatchMessage(parsed.value);
        else
          rejectMessage(parsed.error);
      };

      websocket.onclose = (): void => {
        if (isCurrent())
          handleClose();
      };

      websocket.onerror = (error): void => {
        if (isCurrent())
          handleError(attempt, error);
      };
    }
    catch (error) {
      const errorMessage = `Failed to create WebSocket connection: ${String(error)}`;
      logger.error(errorMessage);
      set(lastError, errorMessage);
      scheduleRetry(attempt);
    }
  }

  /**
   * Opens the bridge socket, or does nothing while one is already open or opening.
   *
   * @remarks
   * Called from a resting phase or during a retry wait, it starts a fresh retry budget immediately.
   */
  function connect(): void {
    const { phase } = get(state);
    if (phase === BridgeConnectionPhase.connecting || phase === BridgeConnectionPhase.connected)
      return;
    openSocket(0);
  }

  /** Closes the socket, including one still handshaking, and cancels any pending retry. */
  function disconnect(): void {
    cancelRetry();
    supersedeSocket();
    set(state, { phase: BridgeConnectionPhase.disconnected });
  }

  // A pending retry or open socket would otherwise outlive its owner.
  onScopeDispose(disconnect, true);

  /**
   * Sends one message over the bridge socket as JSON.
   *
   * @remarks
   * The message is dropped without error while the socket is not open, so a return from here is
   * not evidence that anything was delivered.
   */
  function sendMessage(message: unknown): void {
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(message));
    }
  }

  function onTakeOver(callback: () => void): void {
    set(onTakeOverCallback, callback);
  }

  const cleanup = (): void => {
    disconnect();
    set(onTakeOverCallback, undefined);
  };

  return {
    cleanup,
    connect,
    disconnect,
    isConnected,
    isConnecting,
    lastError: readonly(lastError),
    onTakeOver,
    state: readonly(state),
  };
}
