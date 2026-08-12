import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { describe, expect, it } from 'vitest';
import { toCounterpartyMappingFields } from '@/modules/assets/admin/counterparty-mapping/counterparty-mapping-fields';
import { resolveText } from '@/modules/core/table/pill/core/text';
import { DisplayKinds, type FieldDef } from '@/modules/core/table/pill/core/types';
import { routeSchemaFromFields } from '@/modules/core/table/route';

const t = (key: string): string => key;

const resolvers: SharedFieldResolvers = {
  formatDate: (value: string): string => value,
  parseDate: (): string | undefined => undefined,
  resolveAssetChain: (): string | undefined => undefined,
  resolveAssetSymbol: (value: string): string => value,
  resolveChainName: (value: string): string => value,
  resolveHex: (value: string): string => value,
  resolveLocationName: (value: string): string => value,
  resolveProtocolName: (value: string): string => `Protocol(${value})`,
  resolveTokenName: (value: string): string => value,
};

const counterparties = (): string[] => ['uniswap-v2', 'curve'];

const fields = (): FieldDef[] => toCounterpartyMappingFields(resolvers, t, counterparties);

describe('toCounterpartyMappingFields', () => {
  it('should filter on the counterparty and its symbol', () => {
    expect(fields().map(field => field.key)).toStrictEqual(['counterparty', 'counterpartySymbol']);
  });

  it('should give each field its short pill label', () => {
    expect(fields().map(field => resolveText(field.label))).toStrictEqual([
      'common.counterparty',
      'asset_management.cex_mapping.asset_symbol',
    ]);
  });

  // The same protocol kind history and the accounting rules use, so a counterparty reads alike
  // wherever it is filtered on.
  it('should draw the counterparty as the shared protocol pill', () => {
    const [counterparty] = fields();

    expect(counterparty.display).toBe(DisplayKinds.COUNTERPARTY);
    expect(counterparty.resolveLabel?.('curve')).toBe('Protocol(curve)');
    expect(counterparty.suggest?.()).toStrictEqual(['uniswap-v2', 'curve']);
  });

  it('should refuse a counterparty it does not offer', () => {
    const [counterparty] = fields();

    expect(counterparty.validate?.('curve')).toBe(true);
    expect(counterparty.validate?.('nonsense')).toBe(false);
  });

  it('should type the symbol rather than pick it', () => {
    const [, symbol] = fields();

    expect(symbol.freeText).toBe(true);
    expect(symbol.suggest).toBeUndefined();
  });

  it('should carry both keys in the url', () => {
    expect(Object.keys(routeSchemaFromFields(fields()).shape).sort()).toStrictEqual([
      'counterparty',
      'counterpartySymbol',
    ]);
  });
});
