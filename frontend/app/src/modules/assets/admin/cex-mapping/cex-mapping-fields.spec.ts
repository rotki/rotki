import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { describe, expect, it } from 'vitest';
import { toCexMappingFields } from '@/modules/assets/admin/cex-mapping/cex-mapping-fields';
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
  resolveLocationName: (value: string): string => `Location(${value})`,
  resolveProtocolName: (value: string): string => value,
  resolveTokenName: (value: string): string => value,
};

const exchanges = (): string[] => ['kraken', 'binance'];

const fields = (): FieldDef[] => toCexMappingFields(resolvers, t, exchanges);

describe('toCexMappingFields', () => {
  // These are the keys the backend takes as ordinary filters; they were `extraParams` only because
  // the request payload never declared `locationSymbol`.
  it('should filter on the exchange and its symbol', () => {
    expect(fields().map(field => field.key)).toStrictEqual(['location', 'locationSymbol']);
  });

  it('should give each field its short pill label', () => {
    expect(fields().map(field => resolveText(field.label))).toStrictEqual([
      'common.exchange',
      'asset_management.cex_mapping.asset_symbol',
    ]);
  });

  it('should draw the exchange as the shared location pill', () => {
    const [location] = fields();

    expect(location.display).toBe(DisplayKinds.LOCATION);
    expect(location.resolveLabel?.('kraken')).toBe('Location(kraken)');
    expect(location.suggest?.()).toStrictEqual(['kraken', 'binance']);
  });

  // The backend reads an unknown location as the common mappings rather than as no rows, so a typo
  // would quietly show the wrong ones.
  it('should refuse an exchange it does not offer', () => {
    const [location] = fields();

    expect(location.validate?.('kraken')).toBe(true);
    expect(location.validate?.('nonsense')).toBe(false);
  });

  // There is no list of every symbol every exchange uses, so it is written rather than picked.
  it('should type the symbol rather than pick it', () => {
    const [, symbol] = fields();

    expect(symbol.freeText).toBe(true);
    expect(symbol.multiple).toBe(false);
    expect(symbol.suggest).toBeUndefined();
  });

  it('should carry both keys in the url', () => {
    expect(Object.keys(routeSchemaFromFields(fields()).shape).sort()).toStrictEqual([
      'location',
      'locationSymbol',
    ]);
  });
});
