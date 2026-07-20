import { describe, expect, it } from 'vitest';
import { sortUsernamesByKeyword } from './sort-usernames';

describe('modules/auth/login/sortUsernamesByKeyword', () => {
  it('should preserve the original order when the search is empty', () => {
    const usernames = ['charlie', 'alice', 'bob'];

    expect(sortUsernamesByKeyword(usernames, '')).toEqual(['charlie', 'alice', 'bob']);
  });

  it('should rank a matching username ahead of a non-matching one', () => {
    const result = sortUsernamesByKeyword(['zebra', 'alice'], 'ali');

    expect(result[0]).toBe('alice');
  });

  it('should not mutate the input array', () => {
    const usernames = ['zebra', 'alice'];

    sortUsernamesByKeyword(usernames, 'ali');

    expect(usernames).toEqual(['zebra', 'alice']);
  });

  it('should handle an empty username list', () => {
    expect(sortUsernamesByKeyword([], 'anything')).toEqual([]);
  });
});
