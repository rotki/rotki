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
 * This is a status validation function for a PUT/PATCH/POST action that
 * also involves calling an external service.
 * @param status The status code of the request 2xx-5xx
 * @return The validity of the status code
 */
export function modifyWithExternalService(status: number): boolean {
  return [200, 400, 409, 502].indexOf(status) >= 0;
}

export function fetchWithExternalService(status: number): boolean {
  return [200, 409, 502].indexOf(status) >= 0;
}
