import { ApiAccountData } from '@/model/action-result';
import { AccountData } from '@/typing/types';
import { assert } from '@/utils/assertions';

export function convertAccountData(accountData: ApiAccountData): AccountData {
  const { tags, label, address } = accountData;
  return {
    address,
    label: label ?? '',
    tags: tags ?? []
  };
}

export function toMap<T, K extends keyof T>(
  array: T[],
  key: K
): { [key: string]: T } {
  const map: { [key: string]: T } = {};
  for (let i = 0; i < array.length; i++) {
    const keyValue = array[i][key];
    assert(typeof keyValue === 'string');
    map[keyValue] = array[i];
  }
  return map;
}
