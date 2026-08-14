import { describe, expect, it } from 'vitest';
import { counterpartyMappingSchema } from '@/modules/assets/admin/counterparty-mapping/counterparty-mapping-form';

const messages = {
  asset: 'asset_missing',
  counterparty: 'counterparty_missing',
  counterpartySymbol: 'symbol_missing',
};

const valid = {
  asset: 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
  counterparty: 'uniswap-v2',
  counterpartySymbol: 'USDC',
};

function messagesFor(state: Record<string, unknown>): string[] {
  const result = counterpartyMappingSchema(messages).safeParse(state);
  if (result.success)
    return [];
  return result.error.issues.map(issue => issue.message);
}

describe('counterpartyMappingSchema', () => {
  it('should accept a fully filled mapping', () => {
    expect(messagesFor(valid)).toEqual([]);
  });

  it.each([
    ['asset', 'asset_missing'],
    ['counterparty', 'counterparty_missing'],
    ['counterpartySymbol', 'symbol_missing'],
  ])('should report %s under its own message when empty', (key, message) => {
    expect(messagesFor({ ...valid, [key]: '' })).toEqual([message]);
  });

  it('should treat a whitespace-only value as empty', () => {
    expect(messagesFor({ ...valid, counterpartySymbol: '  \t ' })).toEqual(['symbol_missing']);
  });

  it('should report every empty field rather than stopping at the first', () => {
    expect(messagesFor({ asset: '', counterparty: '', counterpartySymbol: '' })).toEqual([
      'asset_missing',
      'counterparty_missing',
      'symbol_missing',
    ]);
  });

  it('should report a missing field under the same message as an empty one', () => {
    expect(messagesFor({ counterparty: 'uniswap-v2', counterpartySymbol: 'USDC' })).toEqual([
      'asset_missing',
    ]);
  });

  it('should build a fresh schema per call', () => {
    const first = counterpartyMappingSchema(messages);
    const second = counterpartyMappingSchema({ ...messages, asset: 'other' });

    expect(first.safeParse({ ...valid, asset: '' }).error?.issues[0]?.message).toBe('asset_missing');
    expect(second.safeParse({ ...valid, asset: '' }).error?.issues[0]?.message).toBe('other');
  });
});
