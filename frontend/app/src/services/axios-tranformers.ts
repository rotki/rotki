import { BigNumber } from '@rotki/common';
import { type AxiosResponseTransformer } from 'axios';
import { transformCase } from '@/utils/text';

const isObject = (data: any): boolean =>
  typeof data === 'object' &&
  data !== null &&
  !(data instanceof RegExp) &&
  !(data instanceof Error) &&
  !(data instanceof Date) &&
  !(data instanceof BigNumber);

const getUpdatedKey = (key: string, camelCase: boolean): string =>
  transformCase(key, camelCase);

const convertKeys = (data: any, camelCase: boolean, skipKey: boolean): any => {
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
    return key;
  });

  return converted;
};

export const snakeCaseTransformer = (data: any): any =>
  convertKeys(data, false, false);

export const camelCaseTransformer = (data: any): any =>
  convertKeys(data, true, false);

export const noRootCamelCaseTransformer = (data: any): any =>
  convertKeys(data, true, true);

const jsonTransformer: AxiosResponseTransformer = (data, headers) => {
  let result = data;
  const contentType = headers?.['content-type'];
  const isJson = contentType?.includes('application/json') ?? false;
  if (isJson && typeof data === 'string') {
    try {
      result = JSON.parse(data);
      // eslint-disable-next-line no-empty
    } catch {}
  }
  return result;
};

export const setupTransformer = (
  skipRoot = false
): AxiosResponseTransformer[] => [
  jsonTransformer,
  skipRoot ? noRootCamelCaseTransformer : camelCaseTransformer
];

export const basicAxiosTransformer = setupTransformer();
