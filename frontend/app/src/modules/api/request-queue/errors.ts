export class QueueOverflowError extends Error {
  constructor(message: string = 'Request queue overflow') {
    super(message);
    this.name = 'QueueOverflowError';
    Object.setPrototypeOf(this, QueueOverflowError.prototype);
  }
}

export class QueueTimeoutError extends Error {
  constructor(message: string = 'Request timed out in queue') {
    super(message);
    this.name = 'QueueTimeoutError';
    Object.setPrototypeOf(this, QueueTimeoutError.prototype);
  }
}

export class RequestCancelledError extends Error {
  constructor(message: string = 'Request was cancelled') {
    super(message);
    this.name = 'RequestCancelledError';
    Object.setPrototypeOf(this, RequestCancelledError.prototype);
  }
}
