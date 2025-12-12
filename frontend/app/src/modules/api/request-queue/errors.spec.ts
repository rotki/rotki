import { describe, expect, it } from 'vitest';
import { QueueOverflowError, QueueTimeoutError, RequestCancelledError } from './errors';

describe('request queue errors', () => {
  describe('queueOverflowError', () => {
    it('should create error with default message', () => {
      const error = new QueueOverflowError();
      expect(error.message).toBe('Request queue overflow');
      expect(error.name).toBe('QueueOverflowError');
      expect(error).toBeInstanceOf(Error);
      expect(error).toBeInstanceOf(QueueOverflowError);
    });

    it('should create error with custom message', () => {
      const error = new QueueOverflowError('Queue is full (100 requests)');
      expect(error.message).toBe('Queue is full (100 requests)');
      expect(error.name).toBe('QueueOverflowError');
    });
  });

  describe('queueTimeoutError', () => {
    it('should create error with default message', () => {
      const error = new QueueTimeoutError();
      expect(error.message).toBe('Request timed out in queue');
      expect(error.name).toBe('QueueTimeoutError');
      expect(error).toBeInstanceOf(Error);
      expect(error).toBeInstanceOf(QueueTimeoutError);
    });

    it('should create error with custom message', () => {
      const error = new QueueTimeoutError('Request waited 60000ms in queue');
      expect(error.message).toBe('Request waited 60000ms in queue');
      expect(error.name).toBe('QueueTimeoutError');
    });
  });

  describe('requestCancelledError', () => {
    it('should create error with default message', () => {
      const error = new RequestCancelledError();
      expect(error.message).toBe('Request was cancelled');
      expect(error.name).toBe('RequestCancelledError');
      expect(error).toBeInstanceOf(Error);
      expect(error).toBeInstanceOf(RequestCancelledError);
    });

    it('should create error with custom message', () => {
      const error = new RequestCancelledError('Cancelled by tag: balances');
      expect(error.message).toBe('Cancelled by tag: balances');
      expect(error.name).toBe('RequestCancelledError');
    });
  });
});
