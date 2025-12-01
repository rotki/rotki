import { describe, expect, it } from 'vitest';
import { serialize } from '@/modules/api/utils';

describe('modules/api/utils', () => {
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
});
