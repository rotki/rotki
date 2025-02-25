import { ApiValidationError } from '@/types/api/errors';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import type { ActionResult } from '@rotki/common';
import type { AxiosInstance, AxiosResponse, ParamsSerializerOptions } from 'axios';
import type { PendingTask } from '@/types/task';

type Parser<T> = (response: AxiosResponse<ActionResult<T>>) => ActionResult<T>;

export function handleResponse<T>(
  response: AxiosResponse<ActionResult<T>>,
  parse: Parser<T> = response => response.data,
): T {
  const { message, result } = parse(response);
  if (result)
    return result;

  if (response.status === 400)
    throw new ApiValidationError(message);

  throw new Error(message);
}

export async function fetchExternalAsync(
  api: AxiosInstance,
  url: string,
  params?: Record<string, any>,
): Promise<PendingTask> {
  const result = await api.get<ActionResult<PendingTask>>(url, {
    params: snakeCaseTransformer({
      asyncQuery: true,
      ...(params || {}),
    }),
    validateStatus: validWithSessionAndExternalService,
  });
  return handleResponse(result);
}

export function serialize(params: Record<string, any>): string {
  const list = [];
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined)
      continue;

    if (Array.isArray(value))
      list.push(`${key}=${value.join(',')}`);
    else list.push(`${key}=${value}`);
  }
  return list.join('&');
}

export const paramsSerializer: ParamsSerializerOptions = {
  serialize,
};

/**
 * Returns true if the provided status code is contained in the array of valid
 * status codes.
 * @param validStatuses An array of valid status codes
 * @param status The supplied status code
 * @return true if the status code is considered valid.
 */
function isValid(validStatuses: number[], status: number): boolean {
  return validStatuses.includes(status);
}

/**
 * Used to validate a status. This validation considers valid responses the following
 * codes 200, 400, 409, or 502. This validation method should be used with requests that take
 * parameters or body payload (code 400), requests that require a logged-in user (code 401) or
 * include the usage of external services 502.
 *
 * An example of a valid use-case for this validator would be for example adding a blockchain account.
 *
 * @param status The status code received in the backend's response
 * @return The validity of the status code
 */
export function validWithParamsSessionAndExternalService(status: number): boolean {
  return isValid([200, 400, 401, 409, 502], status);
}

/**
 * Used to validate a status. This validation considers valid responses the following
 * codes 200, 400, 401, 403, 409, or 502. This validation method should be used with requests that require
 * a logged-in user (code 401) or include the usage of external services 502.
 *
 * An example of a valid use-case for this validator would be fetching all the defi data from
 * the Zerion SDK.
 *
 * @param status The status code received in the backend's response
 * @return The validity of the status code
 */
export function validWithSessionAndExternalService(status: number): boolean {
  return isValid([200, 400, 401, 403, 409, 502], status);
}

/**
 * Used to validate a status. This validation considers valid responses the following
 * codes 200, 400, or 409. This validation method should be used with requests that take
 * parameters or body payload (code 400), and requests that require a logged-in user (code 401).
 *
 * This is the most common combination of responses from the backend
 *
 * @param status The status code received in the backend's response
 * @return The validity of the status code
 */
export function validStatus(status: number): boolean {
  return isValid([200, 400, 401, 409], status);
}

/**
 * Used to validate a status. This validation considers valid responses the following
 * codes 200, 400, 409, or 507. This validation method should be used with requests that take
 * perform a file operation, take parameters, and that require a logged-in user (code 401).
 *
 * @param status The status code received in the backend's response
 * @return The validity of the status code
 */
export function validFileOperationStatus(status: number): boolean {
  return isValid([200, 400, 401, 507], status);
}

/**
 * Used to validate a status. This validation considers valid responses the following
 * codes 200 or 400. This validation method should be used with requests that take
 * parameters or body payload (code 400).
 *
 * This is most commonly used with methods that don't require a logged user and
 * accept parameters or a payload.
 *
 * @param status The status code received in the backend's response
 * @return The validity of the status code
 */
export function validWithoutSessionStatus(status: number): boolean {
  return isValid([200, 400], status);
}

/**
 * Used to validate a status. This validation considers valid responses the following
 * codes 200, 401 or 409. This validation method should be used with requests that require a
 * logged-in user (code 401).
 *
 * This is most commonly used with get methods that accept no parameters
 *
 * @param status The status code received in the backend's response
 * @return The validity of the status code
 */
export function validWithSessionStatus(status: number): boolean {
  return isValid([200, 401, 409], status);
}

/**
 * Used to validate a status. This validation considers valid responses the following
 * codes 200, 300, 400, 401, or 409.
 *
 * This validation is solely used with the user account endpoint.
 *
 * @param status The status code received in the backend's response
 * @return The validity of the status code
 */
export function validAccountOperationStatus(status: number): boolean {
  return isValid([200, 300, 400, 401, 409, 542], status);
}

/**
 * Used to validate a status. This validation considers valid responses the following
 * codes 200, 400, 401 or 409. This validation method should be used with requests that
 * take parameters or body payload (code 400), and requests that require a logged-in
 * user (code 401). The method also checks for authorization (code 401).
 *
 * @param status The status code received in the backend's response
 * @return The validity of the status code
 */
export function validAuthorizedStatus(status: number): boolean {
  return isValid([200, 400, 401, 409], status);
}

/**
 * Used to validate a status. This validation considers valid responses the following
 * codes 200, 400, 404, 409 or 502. This validation method should be used with
 * requests that take parameters or body payload (code 400), and requests that
 * require a logged-in user (code 401).
 *
 * The method also checks for not found (code 404) and remote errors (502)
 *
 * This validation is solely used with the task endpoints.
 *
 * @param status The status code received in the backend's response
 * @return The validity of the status code
 */
export function validTaskStatus(status: number): boolean {
  return isValid([200, 400, 401, 404, 502], status);
}
