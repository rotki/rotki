import type { ActionResult } from '@rotki/common';
import type { AxiosResponse } from 'axios';
import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '@/services/rotkehlchen-api';
import {
  fetchExternalAsync,
  handleResponse,
  serialize,
  validAccountOperationStatus,
  validAuthorizedStatus,
  validFileOperationStatus,
  validStatus,
  validTaskStatus,
  validWithoutSessionStatus,
  validWithParamsSessionAndExternalService,
  validWithSessionAndExternalService,
  validWithSessionStatus,
} from '@/services/utils';
import { ApiValidationError } from '@/types/api/errors';
import { HTTPStatus } from '@/types/api/http';

const backendUrl = process.env.VITE_BACKEND_URL;

function createMockResponse<T>(result: T | null, message: string, status: number): AxiosResponse<ActionResult<T | null>> {
  return {
    config: {} as any,
    data: { message, result },
    headers: {},
    status,
    statusText: 'OK',
  };
}

describe('services/utils', () => {
  describe('handleResponse', () => {
    it('should return result when present', () => {
      const response = createMockResponse({ data: 'test' }, '', HTTPStatus.OK);
      const result = handleResponse(response);
      expect(result).toEqual({ data: 'test' });
    });

    it('should throw ApiValidationError on 400 status with no result', () => {
      const response = createMockResponse(null, 'Validation failed', HTTPStatus.BAD_REQUEST);
      expect(() => handleResponse(response)).toThrow(ApiValidationError);
      expect(() => handleResponse(response)).toThrow('Validation failed');
    });

    it('should throw Error on non-400 status with no result', () => {
      const response = createMockResponse(null, 'Server error', HTTPStatus.INTERNAL_SERVER_ERROR);
      expect(() => handleResponse(response)).toThrow(Error);
      expect(() => handleResponse(response)).toThrow('Server error');
    });

    it('should use custom parser when provided', () => {
      const response = createMockResponse({ nested: { value: 42 } }, '', HTTPStatus.OK);
      const customParser = (res: AxiosResponse<ActionResult<any>>): ActionResult<any> => ({
        message: res.data.message,
        result: res.data.result?.nested,
      });
      const result = handleResponse(response, customParser);
      expect(result).toEqual({ value: 42 });
    });

    it('should handle empty result with message on 200', () => {
      const response = createMockResponse(null, 'Operation completed but no result', HTTPStatus.OK);
      expect(() => handleResponse(response)).toThrow('Operation completed but no result');
    });
  });

  describe('serialize', () => {
    it('should serialize simple key-value pairs', () => {
      const result = serialize({ foo: 'bar', baz: 123 });
      expect(result).toBe('foo=bar&baz=123');
    });

    it('should serialize arrays with comma separation', () => {
      const result = serialize({ tags: ['a', 'b', 'c'] });
      expect(result).toBe('tags=a,b,c');
    });

    it('should skip null and undefined values', () => {
      const result = serialize({ foo: 'bar', empty: null, missing: undefined, baz: 'qux' });
      expect(result).toBe('foo=bar&baz=qux');
    });

    it('should handle empty object', () => {
      const result = serialize({});
      expect(result).toBe('');
    });

    it('should handle mixed types', () => {
      const result = serialize({ str: 'value', num: 42, arr: [1, 2], skip: null });
      expect(result).toBe('str=value&num=42&arr=1,2');
    });
  });

  describe('status validators', () => {
    describe('validWithParamsSessionAndExternalService', () => {
      it.each([
        HTTPStatus.OK,
        HTTPStatus.BAD_REQUEST,
        HTTPStatus.UNAUTHORIZED,
        HTTPStatus.CONFLICT,
        HTTPStatus.BAD_GATEWAY,
      ])('should return true for status %d', (status) => {
        expect(validWithParamsSessionAndExternalService(status)).toBe(true);
      });

      it.each([
        HTTPStatus.CREATED,
        HTTPStatus.FORBIDDEN,
        HTTPStatus.NOT_FOUND,
        HTTPStatus.INTERNAL_SERVER_ERROR,
        HTTPStatus.SERVICE_UNAVAILABLE,
      ])('should return false for status %d', (status) => {
        expect(validWithParamsSessionAndExternalService(status)).toBe(false);
      });
    });

    describe('validWithSessionAndExternalService', () => {
      it.each([
        HTTPStatus.OK,
        HTTPStatus.BAD_REQUEST,
        HTTPStatus.UNAUTHORIZED,
        HTTPStatus.FORBIDDEN,
        HTTPStatus.CONFLICT,
        HTTPStatus.BAD_GATEWAY,
      ])('should return true for status %d', (status) => {
        expect(validWithSessionAndExternalService(status)).toBe(true);
      });

      it.each([
        HTTPStatus.CREATED,
        HTTPStatus.NOT_FOUND,
        HTTPStatus.INTERNAL_SERVER_ERROR,
        HTTPStatus.SERVICE_UNAVAILABLE,
      ])('should return false for status %d', (status) => {
        expect(validWithSessionAndExternalService(status)).toBe(false);
      });
    });

    describe('validStatus', () => {
      it.each([
        HTTPStatus.OK,
        HTTPStatus.BAD_REQUEST,
        HTTPStatus.UNAUTHORIZED,
        HTTPStatus.CONFLICT,
      ])('should return true for status %d', (status) => {
        expect(validStatus(status)).toBe(true);
      });

      it.each([
        HTTPStatus.CREATED,
        HTTPStatus.FORBIDDEN,
        HTTPStatus.NOT_FOUND,
        HTTPStatus.INTERNAL_SERVER_ERROR,
        HTTPStatus.BAD_GATEWAY,
      ])('should return false for status %d', (status) => {
        expect(validStatus(status)).toBe(false);
      });
    });

    describe('validFileOperationStatus', () => {
      it.each([
        HTTPStatus.OK,
        HTTPStatus.BAD_REQUEST,
        HTTPStatus.UNAUTHORIZED,
        HTTPStatus.INSUFFICIENT_STORAGE,
      ])('should return true for status %d', (status) => {
        expect(validFileOperationStatus(status)).toBe(true);
      });

      it.each([
        HTTPStatus.CREATED,
        HTTPStatus.FORBIDDEN,
        HTTPStatus.NOT_FOUND,
        HTTPStatus.CONFLICT,
        HTTPStatus.INTERNAL_SERVER_ERROR,
        HTTPStatus.BAD_GATEWAY,
      ])('should return false for status %d', (status) => {
        expect(validFileOperationStatus(status)).toBe(false);
      });
    });

    describe('validWithoutSessionStatus', () => {
      it.each([
        HTTPStatus.OK,
        HTTPStatus.BAD_REQUEST,
      ])('should return true for status %d', (status) => {
        expect(validWithoutSessionStatus(status)).toBe(true);
      });

      it.each([
        HTTPStatus.CREATED,
        HTTPStatus.UNAUTHORIZED,
        HTTPStatus.FORBIDDEN,
        HTTPStatus.NOT_FOUND,
        HTTPStatus.CONFLICT,
        HTTPStatus.INTERNAL_SERVER_ERROR,
        HTTPStatus.BAD_GATEWAY,
      ])('should return false for status %d', (status) => {
        expect(validWithoutSessionStatus(status)).toBe(false);
      });
    });

    describe('validWithSessionStatus', () => {
      it.each([
        HTTPStatus.OK,
        HTTPStatus.UNAUTHORIZED,
        HTTPStatus.CONFLICT,
      ])('should return true for status %d', (status) => {
        expect(validWithSessionStatus(status)).toBe(true);
      });

      it.each([
        HTTPStatus.CREATED,
        HTTPStatus.BAD_REQUEST,
        HTTPStatus.FORBIDDEN,
        HTTPStatus.NOT_FOUND,
        HTTPStatus.INTERNAL_SERVER_ERROR,
        HTTPStatus.BAD_GATEWAY,
      ])('should return false for status %d', (status) => {
        expect(validWithSessionStatus(status)).toBe(false);
      });
    });

    describe('validAccountOperationStatus', () => {
      it.each([
        HTTPStatus.OK,
        HTTPStatus.MULTIPLE_CHOICES,
        HTTPStatus.BAD_REQUEST,
        HTTPStatus.UNAUTHORIZED,
        HTTPStatus.CONFLICT,
        HTTPStatus.DB_UPGRADE_ERROR,
      ])('should return true for status %d', (status) => {
        expect(validAccountOperationStatus(status)).toBe(true);
      });

      it.each([
        HTTPStatus.CREATED,
        HTTPStatus.FORBIDDEN,
        HTTPStatus.NOT_FOUND,
        HTTPStatus.INTERNAL_SERVER_ERROR,
        HTTPStatus.BAD_GATEWAY,
      ])('should return false for status %d', (status) => {
        expect(validAccountOperationStatus(status)).toBe(false);
      });
    });

    describe('validAuthorizedStatus', () => {
      it.each([
        HTTPStatus.OK,
        HTTPStatus.BAD_REQUEST,
        HTTPStatus.UNAUTHORIZED,
        HTTPStatus.CONFLICT,
      ])('should return true for status %d', (status) => {
        expect(validAuthorizedStatus(status)).toBe(true);
      });

      it.each([
        HTTPStatus.CREATED,
        HTTPStatus.FORBIDDEN,
        HTTPStatus.NOT_FOUND,
        HTTPStatus.INTERNAL_SERVER_ERROR,
        HTTPStatus.BAD_GATEWAY,
      ])('should return false for status %d', (status) => {
        expect(validAuthorizedStatus(status)).toBe(false);
      });
    });

    describe('validTaskStatus', () => {
      it.each([
        HTTPStatus.OK,
        HTTPStatus.BAD_REQUEST,
        HTTPStatus.UNAUTHORIZED,
        HTTPStatus.NOT_FOUND,
        HTTPStatus.BAD_GATEWAY,
      ])('should return true for status %d', (status) => {
        expect(validTaskStatus(status)).toBe(true);
      });

      it.each([
        HTTPStatus.CREATED,
        HTTPStatus.FORBIDDEN,
        HTTPStatus.CONFLICT,
        HTTPStatus.INTERNAL_SERVER_ERROR,
        HTTPStatus.SERVICE_UNAVAILABLE,
      ])('should return false for status %d', (status) => {
        expect(validTaskStatus(status)).toBe(false);
      });
    });
  });

  describe('fetchExternalAsync', () => {
    beforeEach(() => {
      vi.clearAllMocks();
    });

    it('should send GET request with asyncQuery parameter set to true', async () => {
      let capturedUrl: URL | undefined;

      server.use(
        http.get(`${backendUrl}/api/1/test-endpoint`, ({ request }) => {
          capturedUrl = new URL(request.url);
          return HttpResponse.json({
            result: { taskId: 123 },
            message: '',
          });
        }),
      );

      const result = await fetchExternalAsync(api.instance, '/test-endpoint');

      expect(capturedUrl).toBeDefined();
      expect(capturedUrl!.searchParams.get('async_query')).toBe('true');
      expect(result.taskId).toBe(123);
    });

    it('should transform additional params to snake_case', async () => {
      let capturedUrl: URL | undefined;

      server.use(
        http.get(`${backendUrl}/api/1/test-endpoint`, ({ request }) => {
          capturedUrl = new URL(request.url);
          return HttpResponse.json({
            result: { taskId: 456 },
            message: '',
          });
        }),
      );

      await fetchExternalAsync(api.instance, '/test-endpoint', {
        someParam: 'value',
        anotherParam: 42,
      });

      expect(capturedUrl).toBeDefined();
      expect(capturedUrl!.searchParams.get('async_query')).toBe('true');
      expect(capturedUrl!.searchParams.get('some_param')).toBe('value');
      expect(capturedUrl!.searchParams.get('another_param')).toBe('42');
    });

    it('should return PendingTask from successful response', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/async-task`, () =>
          HttpResponse.json({
            result: { taskId: 789 },
            message: '',
          })),
      );

      const result = await fetchExternalAsync(api.instance, '/async-task');

      expect(result).toEqual({ taskId: 789 });
    });

    it('should throw error when result is null', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/failing-endpoint`, () =>
          HttpResponse.json({
            result: null,
            message: 'External service unavailable',
          })),
      );

      await expect(fetchExternalAsync(api.instance, '/failing-endpoint'))
        .rejects
        .toThrow('External service unavailable');
    });

    it('should use validWithSessionAndExternalService validator (accepts 502)', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/external-service`, () =>
          HttpResponse.json({
            result: null,
            message: 'Bad gateway from external service',
          }, { status: HTTPStatus.BAD_GATEWAY })),
      );

      // Should not throw network error, but should throw from handleResponse
      await expect(fetchExternalAsync(api.instance, '/external-service'))
        .rejects
        .toThrow('Bad gateway from external service');
    });
  });
});
