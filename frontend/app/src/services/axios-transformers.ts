import { BigNumber } from '@rotki/common';
import type { AxiosResponseHeaders, AxiosResponseTransformer } from 'axios';

function isObject(data: any): boolean {
  return (
    typeof data === 'object'
    && data !== null
    && !(data instanceof RegExp)
    && !(data instanceof Error)
    && !(data instanceof Date)
    && !(data instanceof BigNumber)
  );
}

function getUpdatedKey(key: string, camelCase: boolean): string {
  return transformCase(key, camelCase);
}

function convertKeys(data: any, camelCase: boolean, skipKey: boolean): any {
  if (Array.isArray(data))
    return data.map(entry => convertKeys(entry, camelCase, false));

  if (!isObject(data))
    return data;

  const converted: Record<string, any> = {};
  Object.keys(data).forEach((key) => {
    const datum = data[key];
    const skipConversion = skipKey || isEvmIdentifier(key) || /^[A-Z]/.test(key);
    const updatedKey = skipConversion ? key : getUpdatedKey(key, camelCase);

    converted[updatedKey] = isObject(datum) ? convertKeys(datum, camelCase, skipKey && key === 'result') : datum;
    return key;
  });

  return converted;
}

export function snakeCaseTransformer(data: any): any {
  return convertKeys(data, false, false);
}

export function camelCaseTransformer(data: any): any {
  return convertKeys(data, true, false);
}

export function noRootCamelCaseTransformer(data: any): any {
  return convertKeys(data, true, true);
}

export function jsonTransformer(data: any, headers: AxiosResponseHeaders): AxiosResponseTransformer {
  let result = data;
  const contentType = headers?.['content-type'];
  const isJson = contentType?.includes('application/json') ?? false;
  if (isJson && typeof data === 'string') {
    try {
      result = JSON.parse(data);
    }
    catch {}
  }
  return result;
}

export function setupTransformer(skipRoot = false): AxiosResponseTransformer[] {
  return [jsonTransformer, skipRoot ? noRootCamelCaseTransformer : camelCaseTransformer];
}

export const basicAxiosTransformer = setupTransformer();
