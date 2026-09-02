import { describe, expect, it } from 'vitest';
import { z } from 'zod';
import { usernameField } from '@/modules/auth/credentials-fields';

describe('usernameField', () => {
  const schema = z.object({
    username: usernameField({ invalid: 'invalid', required: 'required' }),
  });

  function messages(username: string): string[] {
    const result = schema.safeParse({ username });
    if (result.success)
      return [];

    return result.error.issues.map(issue => issue.message);
  }

  it.each([
    ['user_name'],
    ['user.name'],
    ['user-name'],
    ['User1'],
    ['1'],
  ])('should accept %s', (username) => {
    expect(messages(username)).toStrictEqual([]);
  });

  it.each([
    ['user name'],
    ['user@name'],
    ['user/name'],
    ['üser'],
  ])('should reject %s as badly formed', (username) => {
    expect(messages(username)).toStrictEqual(['invalid']);
  });

  it('should report both messages for an empty name, format first', () => {
    expect(messages('')).toStrictEqual(['invalid', 'required']);
  });

  it('should report both messages for a whitespace-only name, since a space is outside the allowed set', () => {
    expect(messages('   ')).toStrictEqual(['invalid', 'required']);
  });
});
