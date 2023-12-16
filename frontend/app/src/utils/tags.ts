import type { MaybeRef } from '@vueuse/core';
import type { GeneralAccountData } from '@/types/blockchain/accounts';

function removeTag(tagName: string, tags?: string[]): string[] | undefined {
  if (!tags)
    return undefined;

  const index = tags.indexOf(tagName);

  if (index < 0)
    return tags;

  return [...tags.slice(0, index), ...tags.slice(index + 1)];
}

export function removeTags<T extends { tags?: string[] }>(data: MaybeRef<T[]>, tagName: string): T[] {
  const accounts = [...get(data)];
  for (let i = 0; i < accounts.length; i++) {
    const account = accounts[i];
    const tags = removeTag(tagName, account.tags);

    if (!tags)
      continue;

    accounts[i] = {
      ...accounts[i],
      tags,
    };
  }
  return accounts;
}

export function getTags(accounts: GeneralAccountData[], address: string): string[] {
  return accounts.find(({ address: addr }) => addr === address)?.tags || [];
}
