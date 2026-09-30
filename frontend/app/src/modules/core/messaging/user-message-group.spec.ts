import type { UserMessageData } from './types/base';
import { describe, expect, it } from 'vitest';
import { userMessageGroup } from './user-message-group';

function badData(overrides: Partial<Extract<UserMessageData, { key: 'bad_data' }>> = {}): UserMessageData {
  return {
    fields: { error: 'Missing key: amount', record: 'balance' },
    key: 'bad_data',
    subject: 'kucoin',
    value: 'Failed to deserialize a kucoin balance',
    verbosity: 'error',
    ...overrides,
  };
}

function authFailure(account: string | null): UserMessageData {
  return {
    fields: { account, service: 'binance' },
    key: 'auth',
    subject: 'binance',
    value: 'Binance rejected the API key',
    verbosity: 'error',
  };
}

describe('userMessageGroup', () => {
  it('should fold repeats of one failure whose error text differs', () => {
    expect(userMessageGroup(badData({ fields: { error: 'Missing key: fee', record: 'balance' }, value: 'other' })))
      .toBe(userMessageGroup(badData()));
  });

  it('should keep unreadable data from different locations apart', () => {
    expect(userMessageGroup(badData({ subject: 'kraken' }))).not.toBe(userMessageGroup(badData()));
  });

  it('should keep unreadable data about different records apart', () => {
    expect(userMessageGroup(badData({ fields: { error: 'Missing key: amount', record: 'trade' } })))
      .not
      .toBe(userMessageGroup(badData()));
  });

  it('should keep a warning apart from an error with the same identity', () => {
    expect(userMessageGroup(badData({ verbosity: 'warning' }))).not.toBe(userMessageGroup(badData()));
  });

  it('should keep rejected credentials apart per account of one service', () => {
    expect(userMessageGroup(authFailure('main'))).not.toBe(userMessageGroup(authFailure('trading')));
    expect(userMessageGroup(authFailure('main'))).toBe(userMessageGroup(authFailure('main')));
  });

  it('should keep unknown assets apart per asset, so each one that needs adding stays visible', () => {
    const unknownAsset = (identifier: string): UserMessageData => ({
      fields: { identifier },
      key: 'unknown_asset',
      subject: null,
      value: `Found unknown asset ${identifier}`,
      verbosity: 'warning',
    });

    expect(userMessageGroup(unknownAsset('FOO'))).not.toBe(userMessageGroup(unknownAsset('BAR')));
    expect(userMessageGroup(unknownAsset('FOO'))).toBe(userMessageGroup(unknownAsset('FOO')));
  });

  it('should name the user message group so cooldowns and lookups recognise it', () => {
    expect(userMessageGroup(badData())).toMatch(/^USER_MESSAGE:/);
  });
});
