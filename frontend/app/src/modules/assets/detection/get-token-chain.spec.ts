import type { EvmChainEntries } from '@/modules/core/api/types/chains';
import { describe, expect, it } from 'vitest';
import { getTokenChain } from './get-token-chain';
import { NewDetectedTokenKind } from './types';

const allEvmChains: EvmChainEntries = [
  { id: 1, label: 'Ethereum', name: 'ethereum' },
  { id: 143, label: 'Monad', name: 'monad' },
  { id: 999, label: 'Hyperliquid', name: 'hyperliquid' },
];

describe('getTokenChain', () => {
  it('should resolve the evm chain name from a Monad token identifier', () => {
    const chain = getTokenChain(
      {
        tokenIdentifier: 'eip155:143/erc20:0x3bd359C1119dA7Da1D913D1C4D2B7c461115433A',
        tokenKind: NewDetectedTokenKind.EVM,
      },
      allEvmChains,
    );

    expect(chain).toBe('monad');
  });

  it('should resolve the evm chain name from a Hyperliquid token identifier', () => {
    const chain = getTokenChain(
      {
        tokenIdentifier: 'eip155:999/erc20:0x5555555555555555555555555555555555555555',
        tokenKind: NewDetectedTokenKind.EVM,
      },
      allEvmChains,
    );

    expect(chain).toBe('hyperliquid');
  });

  it('should resolve the evm chain name from an Ethereum token identifier', () => {
    const chain = getTokenChain(
      {
        tokenIdentifier: 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F',
        tokenKind: NewDetectedTokenKind.EVM,
      },
      allEvmChains,
    );

    expect(chain).toBe('ethereum');
  });

  it('should fall back to the token kind when the chain id is not in the supported chains list', () => {
    const chain = getTokenChain(
      {
        tokenIdentifier: 'eip155:424242/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F',
        tokenKind: NewDetectedTokenKind.EVM,
      },
      allEvmChains,
    );

    expect(chain).toBe(NewDetectedTokenKind.EVM);
  });

  it('should fall back to the token kind when the identifier is malformed', () => {
    const chain = getTokenChain(
      {
        tokenIdentifier: 'not-an-evm-identifier',
        tokenKind: NewDetectedTokenKind.EVM,
      },
      allEvmChains,
    );

    expect(chain).toBe(NewDetectedTokenKind.EVM);
  });

  it('should return the solana token kind for solana tokens regardless of the supported chains list', () => {
    const chain = getTokenChain(
      {
        tokenIdentifier: 'solana/token:So11111111111111111111111111111111111111112',
        tokenKind: NewDetectedTokenKind.SOLANA,
      },
      allEvmChains,
    );

    expect(chain).toBe(NewDetectedTokenKind.SOLANA);
  });
});
