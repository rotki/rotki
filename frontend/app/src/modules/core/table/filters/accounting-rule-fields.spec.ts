import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { describe, expect, it } from 'vitest';
import { toAccountingRuleFields } from '@/modules/core/table/filters/accounting-rule-fields';
import {
  AccountingRuleFilterKeys,
  AccountingRuleFilterValueKeys,
  type Matcher,
} from '@/modules/core/table/filters/use-accounting-rule-filter';
import { DisplayKinds } from '@/modules/core/table/pill/core/types';

const t = (key: string): string => key;

/** Stands in for the backend event mappings the table names its rows with. */
const names = {
  eventSubtypeName: (value: string): string => (value === 'deposit asset' ? 'Deposit Asset' : value),
  eventTypeName: (value: string): string => (value === 'deposit' ? 'Deposit' : value),
};

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

const matchers: Matcher[] = [
  {
    description: 'filter by event type',
    key: AccountingRuleFilterKeys.EVENT_TYPE,
    keyValue: AccountingRuleFilterValueKeys.EVENT_TYPE,
    multiple: true,
    string: true,
    suggestions: (): string[] => ['deposit'],
    validate: (): boolean => true,
  },
  {
    description: 'filter by event sub type',
    key: AccountingRuleFilterKeys.EVENT_SUBTYPE,
    keyValue: AccountingRuleFilterValueKeys.EVENT_SUBTYPE,
    multiple: true,
    string: true,
    suggestions: (): string[] => ['deposit asset'],
    validate: (): boolean => true,
  },
  {
    description: 'filter by counterparty',
    key: AccountingRuleFilterKeys.COUNTERPARTY,
    keyValue: AccountingRuleFilterValueKeys.COUNTERPARTY,
    multiple: true,
    string: true,
    suggestions: (): string[] => ['uniswap-v2'],
    validate: (): boolean => true,
  },
];

describe('toAccountingRuleFields', () => {
  it('should keep the wire keys the table already sends', () => {
    expect(toAccountingRuleFields(matchers, resolvers, t, names).map(field => field.key)).toStrictEqual([
      'eventTypes',
      'eventSubtypes',
      'counterparties',
    ]);
  });

  it('should give each field its short pill label', () => {
    expect(toAccountingRuleFields(matchers, resolvers, t, names).map(field => field.label)).toStrictEqual([
      'accounting_settings.rule.filter_field_labels.event_type',
      'accounting_settings.rule.filter_field_labels.event_subtype',
      'accounting_settings.rule.filter_field_labels.counterparty',
    ]);
  });

  it('should draw the counterparty as the shared protocol pill', () => {
    const [,, counterparty] = toAccountingRuleFields(matchers, resolvers, t, names);

    expect(counterparty.display).toBe(DisplayKinds.COUNTERPARTY);
    expect(counterparty.resolveLabel?.('uniswap-v2')).toBe('Uniswap V2');
    expect(counterparty.suggest?.()).toStrictEqual(['uniswap-v2']);
  });

  // The table names the same values through the backend's event mappings, so the pill uses them
  // too. Casing the raw token instead read "Deposit asset" beside a row saying "Deposit Asset",
  // and would have stayed English in every other locale.
  it('should name the type and subtype the way the table does', () => {
    const [type, subtype] = toAccountingRuleFields(matchers, resolvers, t, names);

    expect(type.resolveLabel?.('deposit')).toBe('Deposit');
    expect(subtype.resolveLabel?.('deposit asset')).toBe('Deposit Asset');
    expect(type.display).toBeUndefined();
  });

  it('should let every field take more than one value, as the matchers do', () => {
    expect(toAccountingRuleFields(matchers, resolvers, t, names).every(field => field.multiple)).toBe(true);
  });
});
