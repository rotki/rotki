import { describe, expect, it } from 'vitest';
import { camelCaseTransformer } from '@/modules/core/api/transformers';
import { BlockchainBalances } from './blockchain-balances';

const ADDRESS = '0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF';

const PAYLOAD = {
  per_account: {
    eth: {
      [ADDRESS]: {
        assets: {
          ETH: {
            lido: {
              amount: '0.5',
              awaiting_claim: '0.5',
              claims: [
                { amount: '0.2', finalized: true, id: '7', requested_at: 1700000000 },
                { amount: '0.3', available_at: 1800000000, finalized: false },
              ],
              value: '1000',
            },
          },
        },
        liabilities: {},
      },
    },
  },
  totals: { assets: {}, liabilities: {} },
};

describe('blockchainBalances', () => {
  it('should keep the dates and status of each withdrawal request sent in snake case', () => {
    const parsed = BlockchainBalances.parse(camelCaseTransformer(PAYLOAD));

    expect(parsed.perAccount).toMatchObject({
      eth: {
        [ADDRESS]: {
          assets: {
            ETH: {
              lido: {
                claims: [
                  { finalized: true, id: '7', requestedAt: 1700000000 },
                  { availableAt: 1800000000, finalized: false },
                ],
              },
            },
          },
        },
      },
    });
  });
});
