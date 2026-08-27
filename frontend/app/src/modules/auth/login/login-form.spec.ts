import { describe, expect, it } from 'vitest';
import { classifyLoginErrors, type LoginFormMessages, loginSchema } from '@/modules/auth/login/login-form';

const MESSAGES: LoginFormMessages = {
  emptyPassword: 'empty-password',
  emptyUrl: 'empty-url',
  invalidUrl: 'invalid-url',
  invalidUsername: 'invalid-username',
  requiredUsername: 'required-username',
};

/** What the backend-url field says, with the rest of the form filled in so only it can report. */
function urlMessages(customBackendUrl: string, backendOpen: boolean = true): string[] {
  const result = loginSchema(MESSAGES, backendOpen).safeParse({
    customBackendUrl,
    password: 'password',
    username: 'user',
  });

  if (result.success)
    return [];

  return result.error.issues
    .filter(issue => issue.path[0] === 'customBackendUrl')
    .map(issue => issue.message);
}

/**
 * The address the app will fetch from, so it is parsed rather than pattern-matched. The rule this
 * replaces reused the shared `isValidUrl`, whose regex demands a dotted host: it took
 * `http://127.0.0.1:4242` and refused `http://localhost:4242`, which name the same machine.
 */
describe('the backend url rule', () => {
  it.each([
    ['http://localhost:4242'],
    ['http://127.0.0.1:4242'],
    ['https://rotki.example.com'],
    ['https://example.com:8080/api'],
    ['http://[::1]:4242'],
    ['http://backend'],
  ])('should accept %s', (value) => {
    expect(urlMessages(value)).toStrictEqual([]);
  });

  it.each([
    ['not a url'],
    ['localhost:4242'],
    ['ftp://example.com'],
    // Only something fetchable is any use here, so anything outside http(s) is out.
    ['javascript:alert(1)'],
    ['file:///etc/passwd'],
  ])('should reject %s', (value) => {
    expect(urlMessages(value)).toStrictEqual(['invalid-url']);
  });

  it('should report both messages for an empty url', () => {
    expect(urlMessages('')).toStrictEqual(['invalid-url', 'empty-url']);
  });

  it('should reject a url of 300 characters or more', () => {
    expect(urlMessages(`http://localhost/${'a'.repeat(300)}`)).toStrictEqual(['invalid-url']);
  });

  it('should accept one just under the bound', () => {
    const prefix = 'http://localhost/';
    const url = `${prefix}${'a'.repeat(299 - prefix.length)}`;
    expect(url).toHaveLength(299);
    expect(urlMessages(url)).toStrictEqual([]);
  });

  it('should say nothing at all while the panel is closed, however bad the field holds', () => {
    expect(urlMessages('not a url', false)).toStrictEqual([]);
    expect(urlMessages('', false)).toStrictEqual([]);
  });
});

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

  it('should keep the first message of each kind', () => {
    expect(classifyLoginErrors(['User a is gone', 'User b is gone'])).toStrictEqual({
      username: ['User a is gone'],
    });
  });
});
