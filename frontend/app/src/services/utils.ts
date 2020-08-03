import { AxiosResponse } from 'axios';
import { ActionResult } from '@/model/action-result';

export function handleResponse<T>(response: AxiosResponse<ActionResult<T>>): T {
  const { result, message } = response.data;
  if (result) {
    return result;
  }
  throw new Error(message);
}

const isValid = (validStatuses: number[], status: number): boolean =>
  validStatuses.indexOf(status) >= 0;

/**
 * This is a status validation function for a PUT/PATCH/POST action that
 * also involves calling an external service.
 * @param status The status code of the request 2xx-5xx
 * @return The validity of the status code
 */
export function validWithSessionAndExternalService(status: number): boolean {
  return isValid([200, 400, 409, 502], status);
}

export function fetchWithExternalService(status: number): boolean {
  return isValid([200, 409, 502], status);
}

export function validStatus(status: number): boolean {
  return isValid([200, 400, 409], status);
}

export function validWithoutSessionStatus(status: number): boolean {
  return isValid([200, 400], status);
}
export function validWithSessionStatus(status: number): boolean {
  return isValid([200, 409], status);
}

export function validSessionStatus(status: number): boolean {
  return isValid([200, 300, 400, 401, 409], status);
}

export function validSessionModifyStatus(status: number): boolean {
  return isValid([200, 400, 401, 409, 502], status);
}

export function validTaskStatus(status: number): boolean {
  return isValid([200, 400, 404, 409], status);
}
