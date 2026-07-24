export class QueueOverflowError extends Error {
  constructor(message: string = 'Request queue overflow', options?: ErrorOptions) {
    super(message, options);
    this.name = 'QueueOverflowError';
    Object.setPrototypeOf(this, QueueOverflowError.prototype);
  }
}

export class QueueTimeoutError extends Error {
  constructor(message: string = 'Request timed out in queue', options?: ErrorOptions) {
    super(message, options);
    this.name = 'QueueTimeoutError';
    Object.setPrototypeOf(this, QueueTimeoutError.prototype);
  }
}

export class RequestCancelledError extends Error {
  constructor(message: string = 'Request was cancelled', options?: ErrorOptions) {
    super(message, options);
    this.name = 'RequestCancelledError';
    Object.setPrototypeOf(this, RequestCancelledError.prototype);
  }
}
