import { z, type ZodType } from 'zod';
import { usernameField } from '@/modules/auth/credentials-fields';
import { requiredField } from '@/modules/core/form/fields';

/** The prefixes the backend puts on a rejection, which are all there is to say which field it means. */
const USERNAME_ERROR_PREFIX = 'User ';
const PASSWORD_ERROR_PREFIX = 'Wrong password ';

/** A url longer than this is refused before it is parsed. */
const MAX_BACKEND_URL_LENGTH = 300;

export interface LoginFormState {
  customBackendUrl: string;
  password: string;
  username: string;
}

export interface LoginFormMessages {
  emptyPassword: string;
  emptyUrl: string;
  invalidUrl: string;
  invalidUsername: string;
  requiredUsername: string;
}

/**
 * An address the app can actually reach a backend on: an http(s) url with a host.
 *
 * The shared `isValidUrl` is not that test. Its regex demands a dotted host, which is right for
 * spotting links in a message but wrong here: it accepted `http://127.0.0.1:4242` and refused
 * `http://localhost:4242`, which name the same machine. Parsing beats pattern-matching for a value
 * whose only job is to be fetched from.
 */
function isBackendUrl(value: string): boolean {
  if (value.length >= MAX_BACKEND_URL_LENGTH)
    return false;

  try {
    const url = new URL(value);
    return (url.protocol === 'http:' || url.protocol === 'https:') && url.hostname.length > 0;
  }
  catch {
    return false;
  }
}

/**
 * The panel holding this field can be closed, in which case none of it is validated. That is a piece
 * of screen state rather than of the credentials, so it parameterises the builder.
 *
 * The length bound shares the format rule's message, as it did before: there is one message bound to
 * this field for both.
 */
function backendUrlField(messages: LoginFormMessages, open: boolean): ZodType<string> {
  return z.string().superRefine((value, ctx) => {
    if (!open)
      return;

    if (!isBackendUrl(value))
      ctx.addIssue({ code: 'custom', message: messages.invalidUrl });

    if (value.trim() === '')
      ctx.addIssue({ code: 'custom', message: messages.emptyUrl });
  });
}

export function loginSchema(messages: LoginFormMessages, backendOpen: boolean): ZodType {
  return z.object({
    customBackendUrl: backendUrlField(messages, backendOpen),
    password: requiredField(messages.emptyPassword),
    username: usernameField({ invalid: messages.invalidUsername, required: messages.requiredUsername }),
  });
}

/**
 * Routes the flat list of messages a failed login comes back with onto the field each one is about.
 *
 * @remarks
 * The backend names the field only through the wording, so this is prefix matching and cannot be
 * better until the api reports errors per field. Match here rather than inline at a call site, so
 * the alert and the fields agree on which prefixes mean a credential problem.
 *
 * @returns fields to their messages; anything matching neither prefix belongs to no field and is
 * left out for the alert to show whole
 */
export function classifyLoginErrors(errors: string[]): Record<string, string[]> {
  const classified: Record<string, string[]> = {};

  const username = errors.find(error => error.startsWith(USERNAME_ERROR_PREFIX));
  if (username)
    classified.username = [username];

  const password = errors.find(error => error.startsWith(PASSWORD_ERROR_PREFIX));
  if (password)
    classified.password = [password];

  return classified;
}
