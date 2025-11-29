import { HTTPStatus } from '@/types/api/http';

export function serialize(params: Record<string, unknown>): string {
  const list: string[] = [];
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined)
      continue;

    if (Array.isArray(value))
      list.push(`${key}=${value.join(',')}`);
    else list.push(`${key}=${String(value)}`);
  }
  return list.join('&');
}

export type ValidStatuses = readonly number[];

/**
 * Default validation: 200, 400, 409.
 * This is the most common validation pattern in the codebase.
 */
export const VALID_STATUS_CODES = [
  HTTPStatus.OK,
  HTTPStatus.BAD_REQUEST,
  HTTPStatus.CONFLICT,
] as const;

/**
 * Extends default validation (200, 400, 409) with 502 Bad Gateway.
 * Use for requests that interact with external services.
 */
export const VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE = [
  HTTPStatus.OK,
  HTTPStatus.BAD_REQUEST,
  HTTPStatus.CONFLICT,
  HTTPStatus.BAD_GATEWAY,
] as const;

/**
 * Extends default validation (200, 400, 409) with 403 Forbidden and 502 Bad Gateway.
 * Use for requests that interact with external services and may return forbidden errors.
 */
export const VALID_WITH_SESSION_AND_EXTERNAL_SERVICE = [
  HTTPStatus.OK,
  HTTPStatus.BAD_REQUEST,
  HTTPStatus.FORBIDDEN,
  HTTPStatus.CONFLICT,
  HTTPStatus.BAD_GATEWAY,
] as const;

/**
 * Extends default validation (200, 400, 409) with 507 Insufficient Storage.
 * Use for file operation requests.
 */
export const VALID_FILE_OPERATION_STATUS = [
  HTTPStatus.OK,
  HTTPStatus.BAD_REQUEST,
  HTTPStatus.CONFLICT,
  HTTPStatus.INSUFFICIENT_STORAGE,
] as const;

/**
 * Validates 200 and 409 responses (excludes 400).
 * Use for session operations that don't expect bad request errors.
 */
export const VALID_WITH_SESSION_STATUS = [
  HTTPStatus.OK,
  HTTPStatus.CONFLICT,
] as const;

/**
 * Validates only 200 and 400 responses.
 * Use for requests that don't require a logged-in user.
 */
export const VALID_WITHOUT_SESSION_STATUS = [
  HTTPStatus.OK,
  HTTPStatus.BAD_REQUEST,
] as const;

/**
 * Extends default validation (200, 400, 409) with 300 Multiple Choices and 412 DB Upgrade Error.
 * Use specifically for user account operations.
 */
export const VALID_ACCOUNT_OPERATION_STATUS = [
  HTTPStatus.OK,
  HTTPStatus.MULTIPLE_CHOICES,
  HTTPStatus.BAD_REQUEST,
  HTTPStatus.CONFLICT,
  HTTPStatus.DB_UPGRADE_ERROR,
] as const;

/**
 * Extends default validation (200, 400, 409) with 404 Not Found and 502 Bad Gateway.
 * Use specifically for task-related endpoints.
 */
export const VALID_TASK_STATUS = [
  HTTPStatus.OK,
  HTTPStatus.BAD_REQUEST,
  HTTPStatus.NOT_FOUND,
  HTTPStatus.CONFLICT,
  HTTPStatus.BAD_GATEWAY,
] as const;
