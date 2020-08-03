import { AxiosResponse } from 'axios';
import { ActionResult } from '@/model/action-result';

export function handleResponse<T>(response: AxiosResponse<ActionResult<T>>): T {
  const { result, message } = response.data;
  if (result) {
    return result;
  }
  throw new Error(message);
}

/**
 * Returns true if the provided status code is contained in the array of valid
 * status codes.
 * @param validStatuses An array of valid status codes
 * @param status The supplied status code
 * @return true if the status code is considered valid.
 */
const isValid = (validStatuses: number[], status: number): boolean =>
  validStatuses.indexOf(status) >= 0;

/**
 * Used to validate a status. This validation considers valid responses the following
 * codes 200, 400, 409, or 502. This validation method should be used with requests that take
 * parameters or body payload (code 400), requests that require a logged in user (code 409) or
 * include the usage of external services 502.
 *
 * An example of a valid use-case for this validator would be for example adding a blockchain account.
 *
 * @param status The status code received in the backend's response
 * @return The validity of the status code
 */
export function validWithParamsSessionAndExternalService(
  status: number
): boolean {
  return isValid([200, 400, 409, 502], status);
}

/**
 * Used to validate a status. This validation considers valid responses the following
 * codes 200, 409, or 502. This validation method should be used with requests that require
 * a logged in user (code 409) or include the usage of external services 502.
 *
 * An example of a valid use-case for this validator would be fetching all the defi data from
 * the Zerion SDK.
 *
 * @param status The status code received in the backend's response
 * @return The validity of the status code
 */
export function validWithSessionAndExternalService(status: number): boolean {
  return isValid([200, 409, 502], status);
}

/**
 * Used to validate a status. This validation considers valid responses the following
 * codes 200, 400, or 409. This validation method should be used with requests that take
 * parameters or body payload (code 400), and requests that require a logged in user (code 409).
 *
 * This is the most common combination of responses from the backend
 *
 * @param status The status code received in the backend's response
 * @return The validity of the status code
 */
export function validStatus(status: number): boolean {
  return isValid([200, 400, 409], status);
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
 * codes 200 or 409. This validation method should be used with requests that require a
 * logged in user (code 409).
 *
 * This is most commonly used with get methods that accept no parameters
 *
 * @param status The status code received in the backend's response
 * @return The validity of the status code
 */
export function validWithSessionStatus(status: number): boolean {
  return isValid([200, 409], status);
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
  return isValid([200, 300, 400, 401, 409], status);
}

/**
 * Used to validate a status. This validation considers valid responses the following
 * codes 200, 400, 401 or 409. This validation method should be used with requests that
 * take parameters or body payload (code 400), and requests that require a logged
 * in user (code 409). The method also checks for authorization (code 401).
 *
 * @param status The status code received in the backend's response
 * @return The validity of the status code
 */
export function validAuthorizedStatus(status: number): boolean {
  return isValid([200, 400, 401, 409], status);
}

/**
 * Used to validate a status. This validation considers valid responses the following
 * codes 200, 400, 404 or 409. This validation method should be used with requests that
 * take parameters or body payload (code 400), and requests that require a logged
 * in user (code 409). The method also checks for not found (code 404).
 *
 * This validation is solely used with the task endpoints.
 *
 * @param status The status code received in the backend's response
 * @return The validity of the status code
 */
export function validTaskStatus(status: number): boolean {
  return isValid([200, 400, 404, 409], status);
}
