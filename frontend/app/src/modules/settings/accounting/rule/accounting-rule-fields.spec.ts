import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { describe, expect, it } from 'vitest';
import { DisplayKinds, type FieldDef } from '@/modules/core/table/pill/core/types';
import { routeSchemaFromFields } from '@/modules/core/table/route';
import { type AccountingRuleFieldOptions, toAccountingRuleFields } from '@/modules/settings/accounting/rule/accounting-rule-fields';

const t = (key: string): string => key;

const resolvers: SharedFieldResolvers = {
  formatDate: (value: string): string => value,
  parseDate: (): string | undefined => undefined,
  resolveAssetChain: (): string | undefined => undefined,
  resolveAssetSymbol: (value: string): string => value,
  resolveChainName: (value: string): string => value,
  resolveHex: (value: string): string => value,
  resolveLocationName: (value: string): string => value,
  resolveProtocolName: (): string => 'Uniswap V2',
  resolveTokenName: (): string => 'Deposit asset',
};

/** The lists and names stand in for the backend event mappings the table reads. */
const options: AccountingRuleFieldOptions = {
  counterparties: (): string[] => ['uniswap-v2'],
  eventSubtypeName: (value: string): string => (value === 'deposit asset' ? 'Deposit Asset' : value),
  eventSubtypes: (): string[] => ['deposit asset'],
  eventTypeName: (value: string): string => (value === 'deposit' ? 'Deposit' : value),
  eventTypes: (): string[] => ['deposit'],
  // What each event type admits, the lookup the subtype field declares as `admits`.
  subtypesFor: (eventTypes: readonly string[]): string[] =>
    eventTypes.includes('deposit') ? ['deposit asset'] : [],
};

const fields = (): FieldDef[] => toAccountingRuleFields(resolvers, t, options);

describe('toAccountingRuleFields', () => {
  // The url shape of the filter bag is derived from these fields, so the round-trip is asserted
  // here rather than against a second hand-written declaration.
  describe('route query', () => {
    it('should coerce single route values into arrays', () => {
      expect(routeSchemaFromFields(fields()).parse({ counterparties: 'uniswap', eventTypes: 'spend' }))
        .toEqual({ counterparties: ['uniswap'], eventTypes: ['spend'] });
    });

    it('should allow an empty route filter', () => {
      expect(routeSchemaFromFields(fields()).parse({})).toEqual({});
    });
  });

  it('should keep the wire keys the table already sends', () => {
    expect(fields().map(field => field.key)).toStrictEqual([
      'eventTypes',
      'eventSubtypes',
      'counterparties',
    ]);
  });

  it('should give each field its short pill label', () => {
    expect(fields().map(field => field.label)).toStrictEqual([
      'accounting_settings.rule.filter_field_labels.event_type',
      'accounting_settings.rule.filter_field_labels.event_subtype',
      'accounting_settings.rule.filter_field_labels.counterparty',
    ]);
  });

  it('should draw the counterparty as the shared protocol pill', () => {
    const [,, counterparty] = fields();

    expect(counterparty.display).toBe(DisplayKinds.COUNTERPARTY);
    expect(counterparty.resolveLabel?.('uniswap-v2')).toBe('Uniswap V2');
    expect(counterparty.suggest?.()).toStrictEqual(['uniswap-v2']);
  });

  it('should offer the types and subtypes the backend knows', () => {
    const [type, subtype] = fields();

    expect(type.suggest?.()).toStrictEqual(['deposit']);
    expect(subtype.suggest?.()).toStrictEqual(['deposit asset']);
  });

  // A rule is written for a type/subtype pair and the request reads the two as a cross product, so
  // a subtype the selected types do not admit matches no rule. The bar drops it through
  // `pruneInadmissible`; here it is the declaration that is pinned.
  it('should admit only the subtypes of the types it is asked about', () => {
    const [, subtype] = fields();

    expect(subtype.admits?.({ eventTypes: ['deposit'] })).toStrictEqual(['deposit asset']);
    expect(subtype.admits?.({ eventTypes: ['spend'] })).toStrictEqual([]);
  });

  // The table names the same values through the backend's event mappings, so the pill uses them
  // too. Casing the raw token instead read "Deposit asset" beside a row saying "Deposit Asset",
  // and would have stayed English in every other locale.
  it('should name the type and subtype the way the table does', () => {
    const [type, subtype] = fields();

    expect(type.resolveLabel?.('deposit')).toBe('Deposit');
    expect(subtype.resolveLabel?.('deposit asset')).toBe('Deposit Asset');
    expect(type.display).toBeUndefined();
  });

  it('should let every field take more than one value', () => {
    expect(fields().every(field => field.multiple)).toBe(true);
  });

  // None of these keys is declared as behaviour-carrying, so the request has no form for an
  // exclusion and the pill must not offer one.
  it('should offer no exclusion on any field', () => {
    for (const field of fields()) {
      expect(field.allowExclusion).toBe(false);
      expect(field.operators).not.toContain('is_not');
    }
  });
});
