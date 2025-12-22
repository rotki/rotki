import type { MaybeRef } from '@vueuse/core';

/**
 * Deduplicates an array of tags using case-insensitive comparison.
 * Keeps the first occurrence of each tag.
 */
export function deduplicateTags(tags: string[]): string[] {
  const result: string[] = [];
  const seen = new Set<string>();
  for (const tag of tags) {
    const tagLower = tag.toLowerCase();
    if (seen.has(tagLower))
      continue;
    seen.add(tagLower);
    result.push(tag);
  }
  return result;
}

/**
 * Renames a tag in a list of tag names (case-insensitive match).
 * Returns a new deduplicated array.
 */
export function renameTagInList(tags: string[], oldName: string, newName: string): string[] {
  const oldNameLower = oldName.toLowerCase();
  const updatedTags = tags.map(tag => (tag.toLowerCase() === oldNameLower ? newName : tag));
  return deduplicateTags(updatedTags);
}

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

  for (let i = 0; i < accounts.length; i++) {
    const account = accounts[i];
    const tags = account.tags;

    if (!tags || tags.length === 0)
      continue;

    accounts[i] = {
      ...account,
      tags: renameTagInList(tags, oldName, newName),
    };
  }

  return accounts;
}
