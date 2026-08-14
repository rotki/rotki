import { describe, expect, it } from 'vitest';
import { classifyLoginErrors } from '@/modules/auth/login/login-form';

/**
 * The backend reports a failed login as a flat list of sentences, so which field a message is about
 * can only be read off its wording. That guesswork is pinned here rather than only through the form,
 * because it is the part most likely to rot: a reworded backend message silently stops reaching the
 * field it belongs to, and the login screen goes on looking healthy.
 */
describe('classifyLoginErrors', () => {
  it('should route a user message to the username', () => {
    expect(classifyLoginErrors(['User john does not exist'])).toStrictEqual({
      username: ['User john does not exist'],
    });
  });

  it('should route a password message to the password', () => {
    expect(classifyLoginErrors(['Wrong password for user john'])).toStrictEqual({
      password: ['Wrong password for user john'],
    });
  });

  it('should route both when both are reported', () => {
    expect(classifyLoginErrors(['User john does not exist', 'Wrong password for user john'])).toStrictEqual({
      password: ['Wrong password for user john'],
      username: ['User john does not exist'],
    });
  });

  // Anything else belongs to no field; the screen shows it whole in its own alert instead.
  it.each([
    ['Something else went wrong'],
    ['user john does not exist'],
    ['The user is already logged in'],
  ])('should claim no field for %s', (message) => {
    expect(classifyLoginErrors([message])).toStrictEqual({});
  });

  it('should claim no field for an empty list', () => {
    expect(classifyLoginErrors([])).toStrictEqual({});
  });

  // Only the first of a kind is shown, which is what the two lookups it replaced did.
  it('should keep the first message of each kind', () => {
    expect(classifyLoginErrors(['User a is gone', 'User b is gone'])).toStrictEqual({
      username: ['User a is gone'],
    });
  });
});
