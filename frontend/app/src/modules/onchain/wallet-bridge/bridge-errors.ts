export class BridgeError extends Error {
  constructor(message: string, public code: string, public cause?: Error) {
    super(message);
    this.name = 'BridgeError';
  }
}

export class BridgeTimeoutError extends BridgeError {
  constructor(operation: string, timeout: number, cause?: Error) {
    super(`Timeout waiting for ${operation} (${timeout}ms)`, 'BRIDGE_TIMEOUT', cause);
    this.name = 'BridgeTimeoutError';
  }
}

export class BridgeConnectionError extends BridgeError {
  constructor(operation: string, cause?: Error) {
    super(`Failed to establish bridge connection during ${operation}`, 'BRIDGE_CONNECTION_ERROR', cause);
    this.name = 'BridgeConnectionError';
  }
}

export class BridgeInitializationError extends BridgeError {
  constructor(reason: string, cause?: Error) {
    super(`Bridge initialization failed: ${reason}`, 'BRIDGE_INIT_ERROR', cause);
    this.name = 'BridgeInitializationError';
  }
}
