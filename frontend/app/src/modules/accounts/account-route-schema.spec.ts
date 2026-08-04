import { describe, expect, it } from 'vitest';
import { AccountExternalFilterSchema } from './account-route-schema';

describe('accounts/account-route-schema', () => {
  describe('chain', () => {
    it('should read the comma-joined form the param source writes', () => {
      const { chain } = AccountExternalFilterSchema.parse({ chain: 'eth,optimism' });

      expect(chain).toEqual(['eth', 'optimism']);
    });

    it('should read the repeated-key form an older link carries', () => {
      const { chain } = AccountExternalFilterSchema.parse({ chain: ['eth', 'optimism'] });

      expect(chain).toEqual(['eth', 'optimism']);
    });

    it('should read a repeated key whose entries are themselves joined', () => {
      const { chain } = AccountExternalFilterSchema.parse({ chain: ['eth,optimism', 'base'] });

      expect(chain).toEqual(['eth', 'optimism', 'base']);
    });

    it('should read a single chain either way', () => {
      expect(AccountExternalFilterSchema.parse({ chain: 'eth' }).chain).toEqual(['eth']);
      expect(AccountExternalFilterSchema.parse({ chain: ['eth'] }).chain).toEqual(['eth']);
    });

    it('should give an empty list when the URL carries no chain', () => {
      expect(AccountExternalFilterSchema.parse({}).chain).toEqual([]);
    });
  });

  describe('the rest of the query', () => {
    it('should split the comma-separated addresses, tags and expanded ids', () => {
      const result = AccountExternalFilterSchema.parse({
        addresses: '0x1,0x2',
        expanded: 'eth-0x1,eth-0x2',
        tags: 'hot,cold',
      });

      expect(result.addresses).toEqual(['0x1', '0x2']);
      expect(result.tags).toEqual(['hot', 'cold']);
      expect(result.expanded).toEqual(['eth-0x1', 'eth-0x2']);
    });

    it('should coerce the tab index and keep the encoded query as it is', () => {
      const result = AccountExternalFilterSchema.parse({ q: 'a%3D1', tab: '2' });

      expect(result.tab).toBe(2);
      expect(result.q).toBe('a%3D1');
    });

    it('should parse an empty query into empty lists', () => {
      expect(AccountExternalFilterSchema.parse({})).toEqual({
        addresses: [],
        chain: [],
        expanded: [],
        tags: [],
      });
    });
  });
});
