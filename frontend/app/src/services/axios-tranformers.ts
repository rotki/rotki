import { BigNumber } from '@rotki/common';
import { AxiosRequestTransformer, AxiosResponseTransformer } from 'axios';
import { isEvmIdentifier } from '@/utils/assets';

const isObject = (data: any): boolean =>
  typeof data === 'object' &&
  data !== null &&
  !(data instanceof RegExp) &&
  !(data instanceof Error) &&
  !(data instanceof Date) &&
  !(data instanceof BigNumber);

export function getUpdatedKey(key: string, camelCase: boolean): string {
  if (camelCase) {
    return key.includes('_')
      ? key.replace(/_(.)/gu, (_, p1) => p1.toUpperCase())
      : key;
  }

  return key.replace(/([A-Z])/gu, (_, p1, offset, string) => {
    const nextCharOffset = offset + 1;
    if (
      (nextCharOffset < string.length &&
        /([A-Z])/.test(string[nextCharOffset])) ||
      nextCharOffset === string.length
    ) {
      return p1;
    }
    return `_${p1.toLowerCase()}`;
  });
}

export const convertKeys = (
  data: any,
  camelCase: boolean,
  skipKey: boolean
): any => {
  if (Array.isArray(data)) {
    return data.map(entry => convertKeys(entry, camelCase, false));
  }

  if (!isObject(data)) {
    return data;
  }

  const converted: Record<string, any> = {};
  Object.keys(data).map(key => {
    const datum = data[key];
    const skipConversion = skipKey || isEvmIdentifier(key);
    const updatedKey = skipConversion ? key : getUpdatedKey(key, camelCase);

    converted[updatedKey] = isObject(datum)
      ? convertKeys(datum, camelCase, skipKey && key === 'result')
      : datum;
  });

  return converted;
};

export const axiosSnakeCaseTransformer: AxiosRequestTransformer = (
  data,
  _headers
) => convertKeys(data, false, false);

export const axiosCamelCaseTransformer: AxiosResponseTransformer = (
  data,
  _headers
) => convertKeys(data, true, false);

export const axiosNoRootCamelCaseTransformer: AxiosResponseTransformer = (
  data,
  _headers
) => convertKeys(data, true, true);

const jsonTransformer: AxiosResponseTransformer = (data, headers) => {
  let result = data;
  const contentType = headers?.['content-type'];
  const isJson = contentType?.includes('application/json') ?? false;
  if (isJson && typeof data === 'string') {
    try {
      result = JSON.parse(data);
      // eslint-disable-next-line no-empty
    } catch (e: any) {}
  }
  return result;
};

export const setupTransformer = (
  skipRoot = false
): AxiosResponseTransformer[] => [
  jsonTransformer,
  skipRoot ? axiosNoRootCamelCaseTransformer : axiosCamelCaseTransformer
];

export const basicAxiosTransformer = setupTransformer();
