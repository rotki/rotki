import { describe, expect, it } from 'vitest';
import { z } from 'zod';
import { usernameField } from '@/modules/auth/credentials-fields';

/**
 * The username rule is the one piece of validation the login form and the create-account form share,
 * so it is pinned here rather than only through each of them. A divergence between the two would let
 * the wizard create an account that login then refuses.
 */
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

  // Both rules report, format first, because vuelidate evaluated every rule and listed them in
  // declaration order. The forms assert the same pair through their own fields.
  it('should report both messages for an empty name', () => {
    expect(messages('')).toStrictEqual(['invalid', 'required']);
  });

  // Whitespace is what separates "present" from "non-empty": it fails the format rule too, since a
  // space is outside the allowed set.
  it('should report both messages for a whitespace-only name', () => {
    expect(messages('   ')).toStrictEqual(['invalid', 'required']);
  });
});
