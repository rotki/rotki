import { FetchError } from 'ofetch';
import { assert, describe, expect, it } from 'vitest';
import { ApiRequestError, ApiValidationError } from '@/modules/core/api/types/errors';
import { createResponseParser, createStatusError, tryParseJson, unwrapResult } from './response-handlers';

function thrownBy(run: () => unknown): unknown {
  try {
    run();
  }
  catch (error: unknown) {
    return error;
  }
  return undefined;
}

describe('response-handlers', () => {
  describe('unwrapResult', () => {
    it('should keep the status and cause of a failure on an allowed status', () => {
      const error = thrownBy(() => unwrapResult({ cause: 'conflict', message: 'taken', result: null }, 409));

      assert(error instanceof ApiRequestError);
      expect(error.message).toBe('taken');
      expect(error.status).toBe(409);
      expect(error.failureCause).toBe('conflict');
    });

    it('should keep the cause on the validation error of a 400', () => {
      const error = thrownBy(() => unwrapResult({ cause: 'invalid_input', message: '{"name":["bad"]}', result: null }, 400));

      assert(error instanceof ApiValidationError);
      expect(error.failureCause).toBe('invalid_input');
      expect(error.errors).toEqual({ name: ['bad'] });
    });

    it('should read a result that names a cause as a failure', () => {
      const error = thrownBy(() => unwrapResult({ cause: 'network', message: 'partial', result: { id: 1 } }, 200));

      assert(error instanceof ApiRequestError);
      expect(error.failureCause).toBe('network');
    });

    it('should fall back to the default value for a failure that names a cause', () => {
      expect(unwrapResult({ cause: 'network', message: 'down', result: null }, 409, 'fallback')).toBe('fallback');
    });

    it('should return a result with no cause, whatever message it carries', () => {
      expect(unwrapResult({ message: 'partial', result: { id: 1 } }, 200)).toEqual({ id: 1 });
    });
  });

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

    it('should return null when the body is not valid JSON', () => {
      const html = '<html><head><title>413 Request Entity Too Large</title></head></html>';

      expect(createResponseParser({})(html)).toBeNull();
      expect(createResponseParser({ skipCamelCase: true })(html)).toBeNull();
      expect(createResponseParser({ skipRootCamelCase: true })(html)).toBeNull();
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

    it('should use a payload-too-large fallback message for 413', () => {
      const error = createStatusError(413);

      expect(error.status).toBe(413);
      expect(error.message).toMatch(/exceeds the limit/i);
    });

    it('should prefer an explicit message over the 413 fallback', () => {
      const error = createStatusError(413, 'Custom message');

      expect(error.message).toBe('Custom message');
    });

    it('should use a backend-unreachable fallback message for 502/503/504', () => {
      for (const status of [502, 503, 504]) {
        const error = createStatusError(status);
        expect(error.status).toBe(status);
        expect(error.message).toMatch(/backend is unreachable/i);
      }
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
