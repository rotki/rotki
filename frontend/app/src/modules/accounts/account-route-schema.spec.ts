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
    it('should split the comma-separated addresses and tags', () => {
      const result = AccountExternalFilterSchema.parse({
        addresses: '0x1,0x2',
        tags: 'hot,cold',
      });

      expect(result.addresses).toEqual(['0x1', '0x2']);
      expect(result.tags).toEqual(['hot', 'cold']);
    });

    it('should leave the details drawer keys to the drawer', () => {
      expect(AccountExternalFilterSchema.parse({ account: '0x1', view: 'chains' })).toEqual({
        addresses: [],
        chain: [],
        tags: [],
      });
    });

    it('should parse an empty query into empty lists', () => {
      expect(AccountExternalFilterSchema.parse({})).toEqual({
        addresses: [],
        chain: [],
        tags: [],
      });
    });
  });
});
