import { AxiosTransformer } from 'axios';
import { default as BigNumber } from 'bignumber.js';

const isNumber = /^-?\d+(\.\d+)?((\d(.\d+)?)?[Ee][-+]\d+)?$/;

const createReviver = (
  numericKeys: string[] | null
): ((key: string, value: any) => any) => (key: string, value: any) => {
  const checkForBN = numericKeys === null || numericKeys.includes(key);
  if (
    checkForBN &&
    value &&
    typeof value === 'string' &&
    isNumber.test(value)
  ) {
    return new BigNumber(value);
  }

  if (numericKeys?.includes(key) && isObject(value)) {
    for (const sub of Object.keys(value)) {
      const valueElement = value[sub];
      if (typeof valueElement === 'string' && isNumber.test(valueElement)) {
        value[sub] = new BigNumber(valueElement);
      }
    }
  }
  return value;
};

const isObject = (data: any): boolean =>
  typeof data === 'object' &&
  data !== null &&
  !(data instanceof RegExp) &&
  !(data instanceof Error) &&
  !(data instanceof Date) &&
  !(data instanceof BigNumber);

function getUpdatedKey(key: string, camelCase: boolean) {
  if (camelCase) {
    return key.includes('_')
      ? key.replace(/_(.)/gu, (_, p1) => p1.toLocaleUpperCase())
      : key;
  }

  return key.replace(/([A-Z])/gu, (_, p1) => `_${p1.toLocaleLowerCase()}`);
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

  const converted: { [key: string]: any } = {};
  Object.keys(data).map(key => {
    const datum = data[key];
    const updatedKey = skipKey ? key : getUpdatedKey(key, camelCase);

    converted[updatedKey] = isObject(datum)
      ? convertKeys(datum, camelCase, skipKey && key === 'result')
      : datum;
  });

  return converted;
};

export const axiosSnakeCaseTransformer: AxiosTransformer = (data, _headers) =>
  convertKeys(data, false, false);

export const axiosCamelCaseTransformer: AxiosTransformer = (data, _headers) =>
  convertKeys(data, true, false);

export const axiosNoRootCamelCaseTransformer: AxiosTransformer = (
  data,
  _headers
) => convertKeys(data, true, true);

export const setupJsonTransformer: (
  numericKeys: string[] | null
) => AxiosTransformer = numericKeys => {
  const reviver = createReviver(numericKeys);
  return (data, _headers) => {
    let result = data;
    if (typeof data === 'string') {
      try {
        result = JSON.parse(data, reviver);
        // eslint-disable-next-line no-empty
      } catch (e) {}
    }
    return result;
  };
};

export function setupTransformer(
  numericKeys: string[] | null = null,
  skipRoot: boolean = false
) {
  return [
    setupJsonTransformer(numericKeys),
    skipRoot ? axiosNoRootCamelCaseTransformer : axiosCamelCaseTransformer
  ];
}
