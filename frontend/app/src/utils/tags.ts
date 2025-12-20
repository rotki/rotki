import type { MaybeRef } from '@vueuse/core';

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

export function renameTags<T extends { tags?: string[] }>(
  data: MaybeRef<T[]>,
  oldName: string,
  newName: string,
): T[] {
  const accounts = [...get(data)];
  const oldNameLower = oldName.toLowerCase();

  for (let i = 0; i < accounts.length; i++) {
    const account = accounts[i];
    const tags = account.tags;

    if (!tags || tags.length === 0)
      continue;

    const updatedTags = tags.map(tag => (tag.toLowerCase() === oldNameLower ? newName : tag));
    const dedupedTags: string[] = [];
    const seen = new Set<string>();
    for (const tag of updatedTags) {
      if (seen.has(tag))
        continue;
      seen.add(tag);
      dedupedTags.push(tag);
    }

    accounts[i] = {
      ...account,
      tags: dedupedTags,
    };
  }

  return accounts;
}
