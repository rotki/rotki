import { type MaybeRef } from '@vueuse/core';
import {
  type BtcAccountData,
  type GeneralAccountData,
  type XpubAccountData
} from '@/types/blockchain/accounts';

const removeTag = (tags: string[] | null, tagName: string): string[] | null => {
  if (!tags) {
    return null;
  }

  const index = tags.indexOf(tagName);

  if (index < 0) {
    return tags;
  }

  return [...tags.slice(0, index), ...tags.slice(index + 1)];
};

export const removeTags = <T extends { tags: string[] | null }>(
  data: MaybeRef<T[]>,
  tagName: string
): T[] => {
  const accounts = [...get(data)];
  for (let i = 0; i < accounts.length; i++) {
    const account = accounts[i];
    const tags = removeTag(account.tags, tagName);

    if (!tags) {
      continue;
    }

    accounts[i] = {
      ...accounts[i],
      tags
    };
  }
  return accounts;
};

export const removeBtcTags = (
  state: MaybeRef<BtcAccountData>,
  tag: string
): BtcAccountData => {
  const accounts = get(state);
  const standalone = removeTags(accounts.standalone, tag);
  const xpubs: XpubAccountData[] = [];

  for (const xpub of accounts.xpubs) {
    xpubs.push({
      ...xpub,
      tags: removeTag(xpub.tags, tag),
      addresses: xpub.addresses ? removeTags(xpub.addresses, tag) : null
    });
  }
  return {
    standalone,
    xpubs
  };
};

export const getTags = (
  accounts: GeneralAccountData[],
  address: string
): string[] =>
  accounts.find(({ address: addr }) => addr === address)?.tags || [];
