import type { UserMessageData } from './types/base';
import { describe, expect, it } from 'vitest';
import { userMessageGroup } from './user-message-group';

function badData(overrides: Partial<Extract<UserMessageData, { key: 'bad_data' }>> = {}): UserMessageData {
  return {
    fields: { error: 'Missing key: amount', record: 'balance' },
    group: ['error', 'bad_data', 'kucoin', 'balance'],
    key: 'bad_data',
    subject: 'kucoin',
    value: 'Failed to deserialize a kucoin balance',
    verbosity: 'error',
    ...overrides,
  };
}

describe('userMessageGroup', () => {
  it('should fold messages with one backend group whose text and error differ', () => {
    expect(userMessageGroup(badData({ fields: { error: 'Missing key: fee', record: 'balance' }, value: 'other' })))
      .toBe(userMessageGroup(badData()));
  });

  it('should keep messages with different backend groups apart', () => {
    expect(userMessageGroup(badData({ group: ['error', 'bad_data', 'kraken', 'balance'] })))
      .not
      .toBe(userMessageGroup(badData()));
  });
});
