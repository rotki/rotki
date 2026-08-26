import { compareTextByKeyword } from '@/modules/core/common/display/assets';

/**
 * Orders saved usernames by how well they match what the user has typed.
 *
 * @remarks
 * Returns a new array rather than sorting in place: the caller's list is backed by shared state,
 * which must not be mutated as a side effect of rendering.
 *
 * @param usernames - the saved profile usernames
 * @param search - the current search input; an empty search preserves the original order
 * @returns the usernames ordered by relevance to the search
 */
export function sortUsernamesByKeyword(usernames: string[], search: string): string[] {
  if (!search)
    return usernames;

  return [...usernames].sort((a, b) => compareTextByKeyword(a, b, search));
}
