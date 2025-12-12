import { describe, expect, it } from 'vitest';
import { transformRequestBody, transformRequestQuery } from './request-transformers';

describe('request-transformers', () => {
  describe('transformRequestBody', () => {
    it('returns null/undefined as-is', () => {
      expect(transformRequestBody(null, {})).toBeNull();
      expect(transformRequestBody(undefined, {})).toBeUndefined();
    });

    it('returns FormData as-is without transformation', () => {
      const formData = new FormData();
      formData.append('key', 'value');

      const result = transformRequestBody(formData, {});

      expect(result).toBe(formData);
    });

    it('converts keys to snake_case by default', () => {
      const body = { userName: 'test', isActive: true };

      const result = transformRequestBody(body, {});

      expect(result).toEqual({ user_name: 'test', is_active: true });
    });

    it('skips snake_case conversion when skipSnakeCase is true', () => {
      const body = { userName: 'test', isActive: true };

      const result = transformRequestBody(body, { skipSnakeCase: true });

      expect(result).toEqual({ userName: 'test', isActive: true });
    });

    it('filters empty properties when filterEmptyProperties is true', () => {
      const body = { userName: 'test', emptyField: null, undefinedField: undefined };

      const result = transformRequestBody(body, { filterEmptyProperties: true });

      expect(result).toEqual({ user_name: 'test' });
    });

    it('filters empty properties with custom options', () => {
      const body = { userName: 'test', emptyString: '', keepThis: null };

      const result = transformRequestBody(body, {
        filterEmptyProperties: { removeEmptyString: true, alwaysPickKeys: ['keepThis'] },
      });

      expect(result).toEqual({ user_name: 'test', keep_this: null });
    });

    it('applies both filtering and snake_case conversion', () => {
      const body = { firstName: 'John', lastName: null, middleName: undefined };

      const result = transformRequestBody(body, { filterEmptyProperties: true });

      expect(result).toEqual({ first_name: 'John' });
    });

    it('handles nested objects', () => {
      const body = { userData: { firstName: 'John', lastName: 'Doe' } };

      const result = transformRequestBody(body, {});

      expect(result).toEqual({ user_data: { first_name: 'John', last_name: 'Doe' } });
    });

    it('handles arrays in body', () => {
      const body = { userIds: [1, 2, 3], tagNames: ['one', 'two'] };

      const result = transformRequestBody(body, {});

      expect(result).toEqual({ user_ids: [1, 2, 3], tag_names: ['one', 'two'] });
    });
  });

  describe('transformRequestQuery', () => {
    it('returns undefined for undefined input', () => {
      const result = transformRequestQuery(undefined, {});

      expect(result).toBeUndefined();
    });

    it('converts keys to snake_case by default', () => {
      const query = { pageSize: 10, sortOrder: 'asc' };

      const result = transformRequestQuery(query, {});

      // queryTransformer converts keys to snake_case but preserves value types
      expect(result).toEqual({ page_size: 10, sort_order: 'asc' });
    });

    it('skips snake_case conversion when skipSnakeCase is true', () => {
      const query = { pageSize: 10, sortOrder: 'asc' };

      const result = transformRequestQuery(query, { skipSnakeCase: true });

      expect(result).toEqual({ pageSize: 10, sortOrder: 'asc' });
    });

    it('filters empty properties when filterEmptyProperties is true', () => {
      const query = { page: 1, filter: null, search: undefined };

      const result = transformRequestQuery(query, { filterEmptyProperties: true });

      // queryTransformer preserves value types
      expect(result).toEqual({ page: 1 });
    });

    it('filters empty strings when removeEmptyString is set', () => {
      const query = { page: 1, search: '', filter: 'active' };

      const result = transformRequestQuery(query, {
        filterEmptyProperties: { removeEmptyString: true },
      });

      // queryTransformer preserves value types (numbers stay as numbers)
      expect(result).toEqual({ page: 1, filter: 'active' });
    });

    it('keeps alwaysPickKeys even if empty', () => {
      const query = { page: 1, required: '', optional: null };

      const result = transformRequestQuery(query, {
        filterEmptyProperties: { alwaysPickKeys: ['required'] },
      });

      // queryTransformer skips null/undefined values, but alwaysPickKeys preserves empty strings
      expect(result).toEqual({ page: 1, required: '' });
    });

    it('handles boolean values', () => {
      const query = { isActive: true, isDeleted: false };

      const result = transformRequestQuery(query, {});

      // queryTransformer converts keys to snake_case but preserves value types
      expect(result).toEqual({ is_active: true, is_deleted: false });
    });

    it('handles numeric values', () => {
      const query = { limit: 100, offset: 0 };

      const result = transformRequestQuery(query, {});

      // queryTransformer converts keys to snake_case but preserves value types
      expect(result).toEqual({ limit: 100, offset: 0 });
    });
  });
});
