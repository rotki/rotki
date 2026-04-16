import { FetchError } from 'ofetch';
import { describe, expect, it } from 'vitest';
import { createResponseParser, createStatusError, tryParseJson } from './response-handlers';

describe('response-handlers', () => {
  describe('createResponseParser', () => {
    it('should return raw JSON parser when skipCamelCase is true', () => {
      const parser = createResponseParser({ skipCamelCase: true });
      const result = parser('{"user_name": "test", "is_active": true}');

      expect(result).toEqual({ user_name: 'test', is_active: true });
    });

    it('should return noRootCamelCase parser when skipRootCamelCase is true', () => {
      const parser = createResponseParser({ skipRootCamelCase: true });
      const result = parser('{"user_name": {"nested_key": "value"}}');

      expect(result).toEqual({ user_name: { nestedKey: 'value' } });
    });

    it('should return full camelCase parser by default', () => {
      const parser = createResponseParser({});
      const result = parser('{"user_name": "test", "is_active": true}');

      expect(result).toEqual({ userName: 'test', isActive: true });
    });

    it('should handle nested objects with camelCase transformation', () => {
      const parser = createResponseParser({});
      const result = parser('{"outer_key": {"inner_key": {"deep_key": "value"}}}');

      expect(result).toEqual({ outerKey: { innerKey: { deepKey: 'value' } } });
    });

    it('should handle arrays with camelCase transformation', () => {
      const parser = createResponseParser({});
      const result = parser('[{"item_name": "first"}, {"item_name": "second"}]');

      expect(result).toEqual([{ itemName: 'first' }, { itemName: 'second' }]);
    });
  });

  describe('createStatusError', () => {
    it('should create FetchError with status and default message', () => {
      const error = createStatusError(404);

      expect(error).toBeInstanceOf(FetchError);
      expect(error.message).toBe('Request failed with status 404');
      expect(error.status).toBe(404);
      expect(error.statusCode).toBe(404);
    });

    it('should create FetchError with custom message', () => {
      const error = createStatusError(500, 'Internal server error');

      expect(error).toBeInstanceOf(FetchError);
      expect(error.message).toBe('Internal server error');
      expect(error.status).toBe(500);
      expect(error.statusCode).toBe(500);
    });

    it('should create FetchError with data payload', () => {
      const data = { errors: ['validation failed'] };
      const error = createStatusError(400, 'Bad request', data);

      expect(error).toBeInstanceOf(FetchError);
      expect(error.data).toEqual(data);
    });

    it('should handle various HTTP status codes', () => {
      const statuses = [400, 401, 403, 404, 409, 500, 502, 503];

      for (const status of statuses) {
        const error = createStatusError(status);
        expect(error.status).toBe(status);
        expect(error.statusCode).toBe(status);
      }
    });
  });

  describe('tryParseJson', () => {
    it('should parse valid JSON string', () => {
      const result = tryParseJson<{ name: string }>('{"name": "test"}');

      expect(result).toEqual({ name: 'test' });
    });

    it('should return null for invalid JSON', () => {
      const result = tryParseJson('not valid json');

      expect(result).toBeNull();
    });

    it('should return null for empty string', () => {
      const result = tryParseJson('');

      expect(result).toBeNull();
    });

    it('should parse arrays', () => {
      const result = tryParseJson<number[]>('[1, 2, 3]');

      expect(result).toEqual([1, 2, 3]);
    });

    it('should parse primitive values', () => {
      expect(tryParseJson('123')).toBe(123);
      expect(tryParseJson('true')).toBe(true);
      expect(tryParseJson('"string"')).toBe('string');
      expect(tryParseJson('null')).toBeNull();
    });

    it('should return null for malformed JSON', () => {
      expect(tryParseJson('{')).toBeNull();
      expect(tryParseJson('{"key":')).toBeNull();
      expect(tryParseJson('[1, 2,')).toBeNull();
    });
  });
});
