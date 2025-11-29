import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defaultApiUrls } from '@/modules/api/api-urls';
import { RotkiApi } from '@/modules/api/rotki-api';
import { ApiValidationError } from '@/types/api/errors';
import { HTTPStatus } from '@/types/api/http';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('modules/api/rotki-api', () => {
  let api: RotkiApi;
  const originalLocation = window.location;

  beforeEach(() => {
    api = new RotkiApi();
    vi.clearAllMocks();

    // Mock window.location
    Object.defineProperty(window, 'location', {
      value: { href: '' },
      writable: true,
    });
  });

  afterEach(() => {
    Object.defineProperty(window, 'location', {
      value: originalLocation,
      writable: true,
    });
  });

  describe('constructor and setup', () => {
    it('initializes with default API URLs', () => {
      expect(api.serverUrl).toBe(defaultApiUrls.coreApiUrl);
      expect(api.baseURL).toBe(`${defaultApiUrls.coreApiUrl}/api/1/`);
    });

    it('returns true for defaultBackend when using default URL', () => {
      expect(api.defaultBackend).toBe(true);
    });

    it('configures custom server URL via setup', () => {
      const customUrl = 'http://custom-server:8080';
      api.setup(customUrl);

      expect(api.serverUrl).toBe(customUrl);
      expect(api.baseURL).toBe(`${customUrl}/api/1/`);
      expect(api.defaultBackend).toBe(false);
    });
  });

  describe('buildUrl', () => {
    it('builds a URL without query parameters', () => {
      const url = api.buildUrl('assets');
      expect(url).toBe(`${api.baseURL}assets`);
    });

    it('builds a URL with query parameters', () => {
      const url = api.buildUrl('assets', { limit: 10, offset: 0 });
      expect(url).toContain('limit=10');
      expect(url).toContain('offset=0');
    });

    it('transforms query keys to snake_case', () => {
      const url = api.buildUrl('assets', { assetType: 'crypto' });
      expect(url).toContain('asset_type=crypto');
    });

    it('skips null and undefined query values', () => {
      const url = api.buildUrl('assets', { limit: 10, filter: null, search: undefined });
      expect(url).toContain('limit=10');
      expect(url).not.toContain('filter');
      expect(url).not.toContain('search');
    });
  });

  describe('fetch - success cases', () => {
    it('makes a successful GET request and unwraps ActionResult', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/test`, () =>
          HttpResponse.json({
            result: { id: 1, name: 'Test' },
            message: '',
          })),
      );

      const result = await api.get<{ id: number; name: string }>('test');

      expect(result).toEqual({ id: 1, name: 'Test' });
    });

    it('makes a successful POST request with body transformation', async () => {
      let capturedBody: unknown;

      server.use(
        http.post(`${backendUrl}/api/1/test`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: { success: true },
            message: '',
          });
        }),
      );

      await api.post('test', { userName: 'test', userAge: 25 });

      expect(capturedBody).toEqual({ user_name: 'test', user_age: 25 });
    });

    it('makes a successful PUT request', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/test`, () =>
          HttpResponse.json({
            result: { updated: true },
            message: '',
          })),
      );

      const result = await api.put<{ updated: boolean }>('test', { id: 1 });

      expect(result).toEqual({ updated: true });
    });

    it('makes a successful PATCH request', async () => {
      server.use(
        http.patch(`${backendUrl}/api/1/test`, () =>
          HttpResponse.json({
            result: { patched: true },
            message: '',
          })),
      );

      const result = await api.patch<{ patched: boolean }>('test', { field: 'value' });

      expect(result).toEqual({ patched: true });
    });

    it('makes a successful DELETE request', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/test`, () =>
          HttpResponse.json({
            result: true,
            message: '',
          })),
      );

      const result = await api.delete<boolean>('test');

      expect(result).toBe(true);
    });

    it('handles falsy result value 0 correctly', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/test`, () =>
          HttpResponse.json({
            result: 0,
            message: '',
          })),
      );

      const result = await api.get<number>('test');
      expect(result).toBe(0);
    });

    it('handles falsy result value false correctly (no message)', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/test`, () =>
          HttpResponse.json({
            result: false,
            message: '',
          })),
      );

      const result = await api.get<boolean>('test');
      expect(result).toBe(false);
    });

    it('handles falsy result value empty string correctly (no message)', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/test`, () =>
          HttpResponse.json({
            result: '',
            message: '',
          })),
      );

      const result = await api.get<string>('test');
      expect(result).toBe('');
    });
  });

  describe('fetch - transformation options', () => {
    it('skips camelCase transformation when skipCamelCase is true', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/test`, () =>
          HttpResponse.json({
            result: { user_name: 'test', created_at: '2024-01-01' },
            message: '',
          })),
      );

      const result = await api.get<{ user_name: string; created_at: string }>('test', { skipCamelCase: true });

      expect(result).toEqual({ user_name: 'test', created_at: '2024-01-01' });
    });

    it('uses noRootCamelCase transformer when skipRootCamelCase is true', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/test`, () =>
          HttpResponse.json({
            result: { _custom_key_: { nested_value: 1 } },
            message: '',
          })),
      );

      const result = await api.get<{ _custom_key_: { nestedValue: number } }>('test', { skipRootCamelCase: true });

      expect(result).toEqual({ _custom_key_: { nestedValue: 1 } });
    });

    it('skips snake_case transformation when skipSnakeCase is true', async () => {
      let capturedBody: unknown;

      server.use(
        http.post(`${backendUrl}/api/1/test`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: { success: true },
            message: '',
          });
        }),
      );

      await api.post('test', { userName: 'test' }, { skipSnakeCase: true });

      expect(capturedBody).toEqual({ userName: 'test' });
    });

    it('does not transform FormData body', async () => {
      let capturedContentType: string | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/upload`, async ({ request }) => {
          capturedContentType = request.headers.get('content-type');
          return HttpResponse.json({
            result: { uploaded: true },
            message: '',
          });
        }),
      );

      const formData = new FormData();
      formData.append('file', new Blob(['content']), 'test.txt');

      await api.post('upload', formData);

      expect(capturedContentType).toContain('multipart/form-data');
    });
  });

  describe('fetch - skipResultUnwrap option', () => {
    it('returns raw response when skipResultUnwrap is true', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/test`, () =>
          HttpResponse.json({
            result: { data: 'test' },
            message: '',
            customField: 'extra',
          })),
      );

      const result = await api.get<{ result: { data: string }; message: string; customField: string }>('test', { skipResultUnwrap: true });

      expect(result).toEqual({
        result: { data: 'test' },
        message: '',
        customField: 'extra',
      });
    });
  });

  describe('fetch - defaultValue option', () => {
    it('returns defaultValue when result is null', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/test`, () =>
          HttpResponse.json({
            result: null,
            message: 'No data found',
          })),
      );

      const result = await api.get<string[]>('test', { defaultValue: [] });

      expect(result).toEqual([]);
    });

    it('returns defaultValue when result is undefined', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/test`, () =>
          HttpResponse.json({
            result: undefined,
            message: 'Not found',
          })),
      );

      const result = await api.get<number>('test', { defaultValue: 0 });

      expect(result).toBe(0);
    });

    it('throws error when result is null and no defaultValue provided', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/test`, () =>
          HttpResponse.json({
            result: null,
            message: 'Error message',
          })),
      );

      await expect(api.get('test')).rejects.toThrow('Error message');
    });
  });

  describe('fetch - treat409AsSuccess option', () => {
    it('returns true when status is 409 and treat409AsSuccess is enabled', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/logout`, () =>
          HttpResponse.json(
            {
              result: null,
              message: 'Already logged out',
            },
            { status: HTTPStatus.CONFLICT },
          )),
      );

      const result = await api.post<boolean>('logout', null, { treat409AsSuccess: true });

      expect(result).toBe(true);
    });

    it('does not treat 409 as success when option is not set', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/test`, () =>
          HttpResponse.json(
            {
              result: null,
              message: 'Conflict error',
            },
            { status: HTTPStatus.CONFLICT },
          )),
      );

      await expect(api.post('test', null)).rejects.toThrow('Conflict error');
    });
  });

  describe('fetch - filterEmptyProperties option', () => {
    it('filters empty properties from body when filterEmptyProperties is true', async () => {
      let capturedBody: unknown;

      server.use(
        http.post(`${backendUrl}/api/1/test`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: { success: true },
            message: '',
          });
        }),
      );

      await api.post('test', {
        name: 'test',
        empty: null,
        arr: [],
        valid: 'value',
      }, { filterEmptyProperties: true });

      expect(capturedBody).toEqual({ name: 'test', valid: 'value' });
    });

    it('filters empty properties from query when filterEmptyProperties is true', async () => {
      let capturedUrl: string = '';

      server.use(
        http.get(`${backendUrl}/api/1/test`, ({ request }) => {
          capturedUrl = request.url;
          return HttpResponse.json({
            result: { success: true },
            message: '',
          });
        }),
      );

      await api.get('test', {
        query: { search: 'query', empty: null, list: [] },
        filterEmptyProperties: true,
      });

      expect(capturedUrl).toContain('search=query');
      expect(capturedUrl).not.toContain('empty');
      expect(capturedUrl).not.toContain('list');
    });

    it('respects alwaysPickKeys option', async () => {
      let capturedBody: unknown;

      server.use(
        http.post(`${backendUrl}/api/1/test`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: { success: true },
            message: '',
          });
        }),
      );

      await api.post('test', {
        name: 'test',
        forceInclude: null,
      }, {
        filterEmptyProperties: { alwaysPickKeys: ['forceInclude'] },
      });

      expect(capturedBody).toEqual({ name: 'test', force_include: null });
    });
  });

  describe('fetch - error handling', () => {
    it('handles 401 unauthorized by calling auth failure action and redirecting', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/test`, () =>
          HttpResponse.json(
            {
              result: null,
              message: 'Unauthorized',
            },
            { status: HTTPStatus.UNAUTHORIZED },
          )),
      );

      const authFailureAction = vi.fn();
      api.setOnAuthFailure(authFailureAction);

      // 401 still throws an error after handling auth failure
      await expect(api.get('test')).rejects.toThrow();

      expect(authFailureAction).toHaveBeenCalled();
      expect(window.location.href).toBe('/#/');
    });

    it('throws ApiValidationError for 400 status with message', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/test`, () =>
          HttpResponse.json(
            {
              result: null,
              message: '{"field": ["Invalid value"]}',
            },
            { status: HTTPStatus.BAD_REQUEST },
          )),
      );

      await expect(api.get('test')).rejects.toThrow(ApiValidationError);
    });

    it('throws error for status codes not in validateStatus', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/test`, () =>
          HttpResponse.json(
            { message: 'Internal error' },
            { status: HTTPStatus.INTERNAL_SERVER_ERROR },
          )),
      );

      await expect(api.get('test')).rejects.toThrow();
    });

    it('throws Error for conflict status with message', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/test`, () =>
          HttpResponse.json(
            {
              result: null,
              message: 'Resource conflict',
            },
            { status: HTTPStatus.CONFLICT },
          )),
      );

      await expect(api.get('test')).rejects.toThrow('Resource conflict');
    });

    it('uses custom validStatuses array', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/test`, () =>
          HttpResponse.json(
            {
              result: { data: 'test' },
              message: '',
            },
            { status: HTTPStatus.CREATED },
          )),
      );

      const result = await api.get<{ data: string }>('test', {
        validStatuses: [HTTPStatus.CREATED],
      });

      expect(result).toEqual({ data: 'test' });
    });

    it('throws error when status is not in validStatuses', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/test`, () =>
          HttpResponse.json(
            { message: 'Not acceptable' },
            { status: HTTPStatus.OK },
          )),
      );

      await expect(
        api.get('test', { validStatuses: [HTTPStatus.CREATED] }),
      ).rejects.toThrow();
    });
  });

  describe('fetch - query transformation', () => {
    it('transforms query keys to snake_case', async () => {
      let capturedUrl: string = '';

      server.use(
        http.get(`${backendUrl}/api/1/assets`, ({ request }) => {
          capturedUrl = request.url;
          return HttpResponse.json({
            result: [],
            message: '',
          });
        }),
      );

      await api.get('assets', { query: { assetType: 'crypto', pageSize: 10 } });

      expect(capturedUrl).toContain('asset_type=crypto');
      expect(capturedUrl).toContain('page_size=10');
    });

    it('joins array query values with commas (not URL-encoded)', async () => {
      let capturedUrl: string = '';

      server.use(
        http.get(`${backendUrl}/api/1/assets`, ({ request }) => {
          capturedUrl = request.url;
          return HttpResponse.json({
            result: [],
            message: '',
          });
        }),
      );

      await api.get('assets', { query: { tags: ['tag1', 'tag2', 'tag3'] } });

      expect(capturedUrl).toContain('tags=tag1,tag2,tag3');
    });
  });

  describe('headStatus', () => {
    it('returns status code for HEAD request', async () => {
      server.use(
        http.head(`${backendUrl}/api/1/resource`, () =>
          new HttpResponse(null, { status: HTTPStatus.OK })),
      );

      const status = await api.headStatus('resource');

      expect(status).toBe(HTTPStatus.OK);
    });

    it('transforms query parameters for HEAD request', async () => {
      let capturedUrl: string = '';

      server.use(
        http.head(`${backendUrl}/api/1/resource`, ({ request }) => {
          capturedUrl = request.url;
          return new HttpResponse(null, { status: HTTPStatus.OK });
        }),
      );

      await api.headStatus('resource', { query: { resourceId: 123 } });

      expect(capturedUrl).toContain('resource_id=123');
    });

    it('handles 401 unauthorized in HEAD request by calling auth failure and throwing', async () => {
      server.use(
        http.head(`${backendUrl}/api/1/resource`, () =>
          new HttpResponse(null, { status: HTTPStatus.UNAUTHORIZED })),
      );

      const authFailureAction = vi.fn();
      api.setOnAuthFailure(authFailureAction);

      // 401 triggers auth failure handling AND throws error (status not in valid list)
      await expect(api.headStatus('resource')).rejects.toThrow();

      expect(authFailureAction).toHaveBeenCalled();
      expect(window.location.href).toBe('/#/');
    });

    it('throws error for invalid status in HEAD request', async () => {
      server.use(
        http.head(`${backendUrl}/api/1/resource`, () =>
          new HttpResponse(null, { status: HTTPStatus.INTERNAL_SERVER_ERROR })),
      );

      await expect(api.headStatus('resource')).rejects.toThrow();
    });
  });

  describe('fetchBlob', () => {
    it('returns blob for successful request', async () => {
      const blobContent = 'test file content';

      server.use(
        http.get(`${backendUrl}/api/1/download`, () =>
          new HttpResponse(blobContent, {
            status: HTTPStatus.OK,
            headers: {
              'Content-Type': 'application/octet-stream',
            },
          })),
      );

      const result = await api.fetchBlob('download');

      expect(result).toBeInstanceOf(Blob);
      const text = await result.text();
      expect(text).toBe(blobContent);
    });

    it('parses JSON error from blob response', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/download`, () =>
          HttpResponse.json(
            { result: null, message: 'Download failed' },
            {
              status: HTTPStatus.OK,
              headers: {
                'Content-Type': 'application/json',
              },
            },
          )),
      );

      await expect(api.fetchBlob('download')).rejects.toThrow('Download failed');
    });

    it('throws TypeError for invalid JSON in error blob', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/download`, () =>
          new HttpResponse('not json', {
            status: HTTPStatus.OK,
            headers: {
              'Content-Type': 'application/json',
            },
          })),
      );

      await expect(api.fetchBlob('download')).rejects.toThrow(TypeError);
    });

    it('handles 401 unauthorized in blob request by calling auth failure and throwing', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/download`, () =>
          new HttpResponse('test', {
            status: HTTPStatus.UNAUTHORIZED,
            headers: {
              'Content-Type': 'application/octet-stream',
            },
          })),
      );

      const authFailureAction = vi.fn();
      api.setOnAuthFailure(authFailureAction);

      // 401 triggers auth failure handling AND throws error (status not in valid list)
      await expect(api.fetchBlob('download')).rejects.toThrow();

      expect(authFailureAction).toHaveBeenCalled();
      expect(window.location.href).toBe('/#/');
    });

    it('transforms body in blob request', async () => {
      let capturedBody: unknown;

      server.use(
        http.post(`${backendUrl}/api/1/download`, async ({ request }) => {
          capturedBody = await request.json();
          return new HttpResponse('file content', {
            status: HTTPStatus.OK,
            headers: {
              'Content-Type': 'application/octet-stream',
            },
          });
        }),
      );

      await api.fetchBlob('download', {
        method: 'POST',
        body: { exportFormat: 'csv' },
      });

      expect(capturedBody).toEqual({ export_format: 'csv' });
    });
  });

  describe('cancel', () => {
    it('allows new requests after cancel', async () => {
      api.cancel();

      server.use(
        http.get(`${backendUrl}/api/1/new-request`, () =>
          HttpResponse.json({
            result: { success: true },
            message: '',
          })),
      );

      const result = await api.get<{ success: boolean }>('new-request');

      expect(result).toEqual({ success: true });
    });
  });

  describe('response transformation - camelCase', () => {
    it('transforms snake_case response keys to camelCase', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/user`, () =>
          HttpResponse.json({
            result: {
              user_id: 1,
              first_name: 'John',
              last_name: 'Doe',
              created_at: '2024-01-01',
              meta_data: {
                last_login: '2024-01-15',
                login_count: 5,
              },
            },
            message: '',
          })),
      );

      const result = await api.get<{
        userId: number;
        firstName: string;
        lastName: string;
        createdAt: string;
        metaData: {
          lastLogin: string;
          loginCount: number;
        };
      }>('user');

      expect(result).toEqual({
        userId: 1,
        firstName: 'John',
        lastName: 'Doe',
        createdAt: '2024-01-01',
        metaData: {
          lastLogin: '2024-01-15',
          loginCount: 5,
        },
      });
    });

    it('transforms nested arrays correctly', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/items`, () =>
          HttpResponse.json({
            result: [
              { item_id: 1, item_name: 'First' },
              { item_id: 2, item_name: 'Second' },
            ],
            message: '',
          })),
      );

      const result = await api.get<Array<{ itemId: number; itemName: string }>>('items');

      expect(result).toEqual([
        { itemId: 1, itemName: 'First' },
        { itemId: 2, itemName: 'Second' },
      ]);
    });
  });

  describe('error response with falsy result and message', () => {
    it('throws error when result is false with a message', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/test`, () =>
          HttpResponse.json({
            result: false,
            message: 'Operation failed',
          })),
      );

      await expect(api.get('test')).rejects.toThrow('Operation failed');
    });

    it('throws error when result is empty string with a message', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/test`, () =>
          HttpResponse.json({
            result: '',
            message: 'Empty result error',
          })),
      );

      await expect(api.get('test')).rejects.toThrow('Empty result error');
    });
  });

  describe('fetch - retry option', () => {
    it('does not retry by default', async () => {
      let callCount = 0;

      server.use(
        http.get(`${backendUrl}/api/1/test`, () => {
          callCount++;
          return HttpResponse.json({
            result: { success: true },
            message: '',
          });
        }),
      );

      await api.get('test');

      expect(callCount).toBe(1);
    });

    it('accepts retry option with boolean true', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/test`, () =>
          HttpResponse.json({
            result: { success: true },
            message: '',
          })),
      );

      // Should not throw - just verifies the option is accepted
      const result = await api.get<{ success: boolean }>('test', { retry: true });

      expect(result).toEqual({ success: true });
    });

    it('accepts retry option with custom configuration', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/test`, () =>
          HttpResponse.json({
            result: { success: true },
            message: '',
          })),
      );

      // Should not throw - just verifies the option is accepted
      const result = await api.get<{ success: boolean }>('test', {
        retry: { maxRetries: 3, retryDelay: 1000 },
      });

      expect(result).toEqual({ success: true });
    });

    it('throws error when request fails without retry', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/test`, () => HttpResponse.error()),
      );

      await expect(api.get('test')).rejects.toThrow();
    });
  });
});
