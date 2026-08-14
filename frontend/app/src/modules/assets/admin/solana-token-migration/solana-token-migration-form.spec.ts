import { describe, expect, it } from 'vitest';
import { solanaTokenMigrationSchema } from '@/modules/assets/admin/solana-token-migration/solana-token-migration-form';

const messages = {
  addressInvalid: 'address_invalid',
  addressMissing: 'address_missing',
  decimalsMissing: 'decimals_missing',
  tokenKindMissing: 'kind_missing',
};

const valid = {
  address: 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
  decimals: 6,
  tokenKind: 'spl-token',
};

function messagesFor(state: Record<string, unknown>): string[] {
  const result = solanaTokenMigrationSchema(messages).safeParse(state);
  if (result.success)
    return [];
  return result.error.issues.map(issue => issue.message);
}

describe('solanaTokenMigrationSchema', () => {
  it('should accept a real mint address', () => {
    expect(messagesFor(valid)).toEqual([]);
  });

  it('should accept zero decimals', () => {
    expect(messagesFor({ ...valid, decimals: 0 })).toEqual([]);
  });

  it('should report a cleared decimals field', () => {
    expect(messagesFor({ ...valid, decimals: null })).toEqual(['decimals_missing']);
  });

  it('should report an empty token kind', () => {
    expect(messagesFor({ ...valid, tokenKind: '' })).toEqual(['kind_missing']);
  });

  it('should report an empty address as missing rather than malformed', () => {
    expect(messagesFor({ ...valid, address: '' })).toEqual(['address_missing']);
  });

  it.each([
    ['not-a-solana-address'],
    ['0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'],
    ['abc'],
  ])('should reject %s as malformed', (address) => {
    expect(messagesFor({ ...valid, address })).toEqual(['address_invalid']);
  });

  it('should carry the fields it does not validate', () => {
    const result = solanaTokenMigrationSchema(messages).safeParse({ ...valid, identifier: 'old' });

    expect(result.success && result.data).toEqual({ ...valid, identifier: 'old' });
  });
});
