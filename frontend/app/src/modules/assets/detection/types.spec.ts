import { describe, expect, it } from 'vitest';
import { NewDetectedToken, NewDetectedTokenKind, NewDetectedTokens } from './types';

describe('handling NewDetectedToken schema', () => {
  it('should parse valid token with all fields', () => {
    const input = {
      tokenIdentifier: 'eip155:1/erc20:0x1234',
      tokenKind: NewDetectedTokenKind.EVM,
      detectedAt: 1700000000000,
      isIgnored: false,
      seenDescription: 'Test token',
      seenTxReference: '0xabc123',
    };

    const result = NewDetectedToken.parse(input);

    expect(result.tokenIdentifier).toBe('eip155:1/erc20:0x1234');
    expect(result.tokenKind).toBe(NewDetectedTokenKind.EVM);
    expect(result.detectedAt).toBe(1700000000000);
    expect(result.isIgnored).toBe(false);
    expect(result.seenDescription).toBe('Test token');
    expect(result.seenTxReference).toBe('0xabc123');
  });

  it('should apply default values for optional fields', () => {
    const input = {
      tokenIdentifier: 'eip155:1/erc20:0x1234',
    };

    const result = NewDetectedToken.parse(input);

    expect(result.tokenIdentifier).toBe('eip155:1/erc20:0x1234');
    expect(result.tokenKind).toBe(NewDetectedTokenKind.EVM); // default
    expect(result.detectedAt).toBeDefined(); // default to Date.now()
    expect(typeof result.detectedAt).toBe('number');
    expect(result.isIgnored).toBeUndefined();
    expect(result.seenDescription).toBeUndefined();
    expect(result.seenTxReference).toBeUndefined();
  });

  it('should parse Solana token kind', () => {
    const input = {
      tokenIdentifier: 'solana:mainnet/spl:TokenAddress',
      tokenKind: NewDetectedTokenKind.SOLANA,
    };

    const result = NewDetectedToken.parse(input);

    expect(result.tokenKind).toBe(NewDetectedTokenKind.SOLANA);
  });

  it('should handle null values for nullable fields', () => {
    const input = {
      tokenIdentifier: 'eip155:1/erc20:0x1234',
      seenDescription: null,
      seenTxReference: null,
    };

    const result = NewDetectedToken.parse(input);

    expect(result.seenDescription).toBeNull();
    expect(result.seenTxReference).toBeNull();
  });

  it('should reject invalid token kind', () => {
    const input = {
      tokenIdentifier: 'eip155:1/erc20:0x1234',
      tokenKind: 'invalid-kind',
    };

    expect(() => NewDetectedToken.parse(input)).toThrow();
  });

  it('should reject missing tokenIdentifier', () => {
    const input = {
      tokenKind: NewDetectedTokenKind.EVM,
    };

    expect(() => NewDetectedToken.parse(input)).toThrow();
  });
});

describe('newDetectedTokens schema (array)', () => {
  it('should parse array of tokens', () => {
    const input = [
      { tokenIdentifier: 'token-1', tokenKind: NewDetectedTokenKind.EVM },
      { tokenIdentifier: 'token-2', tokenKind: NewDetectedTokenKind.SOLANA },
    ];

    const result = NewDetectedTokens.parse(input);

    expect(result).toHaveLength(2);
    expect(result[0].tokenIdentifier).toBe('token-1');
    expect(result[1].tokenIdentifier).toBe('token-2');
  });

  it('should parse empty array', () => {
    const result = NewDetectedTokens.parse([]);

    expect(result).toEqual([]);
  });

  it('should apply defaults to each token in array', () => {
    const input = [
      { tokenIdentifier: 'token-1' },
      { tokenIdentifier: 'token-2' },
    ];

    const result = NewDetectedTokens.parse(input);

    expect(result[0].tokenKind).toBe(NewDetectedTokenKind.EVM);
    expect(result[0].detectedAt).toBeDefined();
    expect(result[1].tokenKind).toBe(NewDetectedTokenKind.EVM);
    expect(result[1].detectedAt).toBeDefined();
  });
});

describe('newDetectedTokenKind enum', () => {
  it('should have correct enum values', () => {
    expect(NewDetectedTokenKind.EVM).toBe('evm');
    expect(NewDetectedTokenKind.SOLANA).toBe('solana');
  });
});
