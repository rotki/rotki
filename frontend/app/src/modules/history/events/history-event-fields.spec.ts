import type { AssetsWithId } from '@/modules/assets/types';
import type { FieldDef, ValueIcon } from '@/modules/core/table/pill/core/types';
import { HistoryEventEntryType } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { FilterBehaviours } from '@/modules/core/table/filtering';
import { transformFilters } from '@/modules/core/table/param-sources';
import { behaviourKeysFromFields, routeSchemaFromFields } from '@/modules/core/table/route';
import { type HistoryEventFieldOptions, toHistoryAccountField, toHistoryActionField, toHistoryEventFields, toHistoryIgnoredField, toHistoryStateField } from '@/modules/history/events/history-event-fields';

const t = (key: string): string => key;
const resolvers = {
  formatDate: (value: string): string => `date:${value}`,
  // The real one reads the user's date format; here anything with two slashes is a date, so the
  // parsing rules stay the parser's own tests and these stay about field assembly.
  parseDate: (value: string): string | undefined => (/^\d+\/\d+\/\d+$/.test(value) ? `ts:${value}` : undefined),
  resolveHex: (value: string): string => `hex:${value}`,
  resolveAssetChain: (value: string): string | undefined => (value.startsWith('eip155:8453') ? 'base' : undefined),
  resolveAssetSymbol: (value: string): string => `symbol:${value}`,
  resolveChainName: (value: string): string => `chain:${value}`,
  resolveEventSubTypeName: (value: string): string => `subtype:${value}`,
  resolveEventTypeName: (value: string): string => `type:${value}`,
  resolveLocationName: (value: string): string => `name:${value}`,
  resolveProtocolName: (value: string): string => `protocol:${value}`,
  resolveTokenName: (value: string): string => `entry:${value}`,
  t,
};

const searchAsset = async (): Promise<AssetsWithId> => [];

function fields(overrides: Partial<HistoryEventFieldOptions> = {}): FieldDef[] {
  return toHistoryEventFields(resolvers, {
    counterparties: (): string[] => ['uniswap-v2'],
    disabled: {},
    entryTypes: undefined,
    eventSubtypes: (): string[] => ['receive_wrapped'],
    eventTypes: (): string[] => ['informational'],
    locations: (): string[] => ['kraken'],
    searchAsset,
    // What each event type admits, the lookup the subtype field declares as `admits`.
    subtypesFor: (eventTypes: readonly string[]): string[] =>
      eventTypes.includes('informational') ? ['receive_wrapped'] : [],
    ...overrides,
  });
}

function fieldOf(key: string, overrides: Partial<HistoryEventFieldOptions> = {}): FieldDef | undefined {
  return fields(overrides).find(field => field.key === key);
}

function keysOf(overrides: Partial<HistoryEventFieldOptions> = {}): string[] {
  return fields(overrides).map(field => field.key);
}

describe('toHistoryEventFields', () => {
  // Both the url shape of the filter bag and the keys the request wraps as `{ behaviour, values }`
  // are derived from these fields, so they are asserted here rather than against a second
  // hand-written declaration that could disagree with the field list.
  describe('route query', () => {
    it('should coerce single route values into arrays where the request takes many', () => {
      expect(routeSchemaFromFields(fields()).parse({ asset: 'ETH', entryTypes: 'evm event', txRefs: '0xabc' }))
        .toEqual({ asset: 'ETH', entryTypes: ['evm event'], txRefs: ['0xabc'] });
    });

    // The period pill collapses the two bounds, which is what the url and the request carry.
    it('should keep the two period bounds as they are sent', () => {
      expect(routeSchemaFromFields(fields()).parse({ fromTimestamp: '1700000000', toTimestamp: '1700086400' }))
        .toEqual({ fromTimestamp: '1700000000', toTimestamp: '1700086400' });
    });

    it('should allow an empty route filter', () => {
      expect(routeSchemaFromFields(fields()).parse({})).toEqual({});
    });
  });

  // The backend takes entry types as `{ behaviour, values }` so a type can be excluded. The pill
  // writes exclusion as a `!` prefix, which is what the URL carries too; the wrapping happens at
  // request assembly, from the keys named here.
  describe('behaviour keys', () => {
    it('should declare entry types as the only behaviour-carrying key', () => {
      expect(behaviourKeysFromFields(fields())).toStrictEqual(['entryTypes']);
    });

    it('should wrap an excluded entry type for the request', () => {
      expect(transformFilters({ entryTypes: ['!evm event'] }, behaviourKeysFromFields(fields())))
        .toStrictEqual({ entryTypes: { behaviour: FilterBehaviours.EXCLUDE, values: ['evm event'] } });
    });
  });

  it('should offer every field in a stable display order when nothing is restricted', () => {
    expect(keysOf()).toStrictEqual([
      'period',
      'asset',
      'notesSubstring',
      'amount',
      'counterparties',
      'location',
      'entryTypes',
      'eventTypes',
      'eventSubtypes',
      'txRefs',
      'addresses',
      'validatorIndices',
    ]);
  });

  it('should send the two amount bounds as one range field', () => {
    expect(fieldOf('amount')).toMatchObject({
      bounds: { lower: 'minAmount', upper: 'maxAmount' },
      label: 'transactions.filter_field_labels.amount',
      valueType: 'range',
    });
  });

  it('should send the two date bounds as one period field', () => {
    expect(fieldOf('period')).toMatchObject({
      bounds: { lower: 'fromTimestamp', upper: 'toTimestamp' },
      valueType: 'date',
    });
  });

  // The one table whose timestamp column is milliseconds: the backend scales both bounds by 1000,
  // so an equal pair asks for the single millisecond `X000` and drops the rest of that second.
  it('should refuse a period whose two bounds name the same second', () => {
    expect(fieldOf('period')?.allowEqualBounds).toBe(false);
  });

  it('should omit the period when the view already fixes it', () => {
    expect(keysOf({ disabled: { period: true } })).not.toContain('period');
  });

  it('should omit the protocol, location and event fields when the view already fixes them', () => {
    const keys = keysOf({ disabled: { eventSubtypes: true, eventTypes: true, locations: true, protocols: true } });

    expect(keys).not.toContain('counterparties');
    expect(keys).not.toContain('location');
    expect(keys).not.toContain('eventTypes');
    expect(keys).not.toContain('eventSubtypes');
  });

  it('should offer the entry type only when more than one is in play', () => {
    expect(keysOf({ entryTypes: [HistoryEventEntryType.EVM_EVENT] })).not.toContain('entryTypes');
    expect(keysOf({
      entryTypes: [HistoryEventEntryType.EVM_EVENT, HistoryEventEntryType.HISTORY_EVENT],
    })).toContain('entryTypes');
    expect(keysOf()).toContain('entryTypes');
  });

  // The one excludable field in the app: the request takes entry types as `{ behaviour, values }`.
  it('should offer exclusion on the entry type alone', () => {
    expect(fieldOf('entryTypes')?.allowExclusion).toBe(true);
    expect(fieldOf('entryTypes')?.operators).toContain('is_not');

    for (const field of fields().filter(field => field.key !== 'entryTypes')) {
      expect(field.allowExclusion).toBe(false);
      expect(field.operators).not.toContain('is_not');
    }
  });

  it('should offer the entry types the view allows, and every one otherwise', () => {
    expect(fieldOf('entryTypes', {
      entryTypes: [HistoryEventEntryType.EVM_EVENT, HistoryEventEntryType.HISTORY_EVENT],
    })?.suggest?.()).toStrictEqual([HistoryEventEntryType.EVM_EVENT, HistoryEventEntryType.HISTORY_EVENT]);
    expect(fieldOf('entryTypes')?.suggest?.()).toStrictEqual(Object.values(HistoryEventEntryType));
  });

  it('should offer the transaction fields only for transaction-bearing entry types', () => {
    const included = keysOf({ entryTypes: [HistoryEventEntryType.EVM_EVENT] });
    expect(included).toContain('txRefs');
    expect(included).toContain('addresses');

    const excluded = keysOf({ entryTypes: [HistoryEventEntryType.ASSET_MOVEMENT_EVENT] });
    expect(excluded).not.toContain('txRefs');
    expect(excluded).not.toContain('addresses');
  });

  it('should offer the validator index only for validator events, and not when fixed', () => {
    expect(keysOf({ entryTypes: [HistoryEventEntryType.ETH_DEPOSIT_EVENT] })).toContain('validatorIndices');
    expect(keysOf({ entryTypes: [HistoryEventEntryType.ASSET_MOVEMENT_EVENT] })).not.toContain('validatorIndices');
    expect(keysOf({
      disabled: { validators: true },
      entryTypes: [HistoryEventEntryType.ETH_DEPOSIT_EVENT],
    })).not.toContain('validatorIndices');
  });

  it('should give every field its short pill label', () => {
    expect(fieldOf('counterparties')?.label).toBe('transactions.filter_field_labels.protocol');
    expect(fieldOf('notesSubstring')?.label).toBe('transactions.filter_field_labels.notes');
    expect(fieldOf('validatorIndices')?.label).toBe('transactions.filter_field_labels.validator_index');
  });

  it('should offer the lists its table knows', () => {
    expect(fieldOf('counterparties')?.suggest?.()).toStrictEqual(['uniswap-v2']);
    expect(fieldOf('location')?.suggest?.()).toStrictEqual(['kraken']);
    expect(fieldOf('eventTypes')?.suggest?.()).toStrictEqual(['informational']);
    expect(fieldOf('eventSubtypes')?.suggest?.()).toStrictEqual(['receive_wrapped']);
  });

  // The offered subtypes narrow with the selected event types, so one the selection no longer
  // admits must not be applied either.
  it('should apply only a subtype the selected event types admit', () => {
    expect(fieldOf('eventSubtypes')?.validate?.('receive_wrapped')).toBe(true);
    expect(fieldOf('eventSubtypes')?.validate?.('spend')).toBe(false);
  });

  // The other half of the same rule: a subtype already picked has to leave the filter once the
  // selected types stop admitting it, or the cross-product query returns nothing. The bar applies
  // this through `pruneInadmissible`; here it is the declaration that is pinned.
  it('should admit only the subtypes of the types it is asked about', () => {
    const admits = fieldOf('eventSubtypes')?.admits;

    expect(admits?.({ eventTypes: ['informational'] })).toStrictEqual(['receive_wrapped']);
    expect(admits?.({ eventTypes: ['spend'] })).toStrictEqual([]);
  });

  it('should search assets through the search its table supplies', () => {
    expect(fieldOf('asset')?.searchAsset).toBe(searchAsset);
  });

  it('should resolve the chain of an asset value, and only for the asset field', () => {
    expect(fieldOf('asset')?.resolveChain?.('eip155:8453/erc20:0x8Fa0')).toBe('base');
    expect(fieldOf('asset')?.resolveChain?.('BTC')).toBeUndefined();
    expect(fieldOf('location')?.resolveChain).toBeUndefined();
  });

  it('should map event type, subtype and entry type values to their display name', () => {
    expect(fieldOf('eventTypes')?.resolveLabel?.('informational')).toBe('type:informational');
    expect(fieldOf('eventSubtypes')?.resolveLabel?.('receive_wrapped')).toBe('subtype:receive_wrapped');
    expect(fieldOf('entryTypes')?.resolveLabel?.('evm event')).toBe('entry:evm event');
  });

  it('should map address values through the address resolver', () => {
    expect(fieldOf('addresses')?.resolveLabel?.('0xabc')).toBe('hex:0xabc');
  });

  // A full hash is both too long for a pill and, in privacy mode, as revealing as an address.
  it('should shorten and scramble tx hash values like addresses', () => {
    expect(fieldOf('txRefs')?.resolveLabel?.('0xdeadbeef')).toBe('hex:0xdeadbeef');
  });

  // A transaction reference may be a signature rather than a hash, which is why it is not the
  // shared hex check.
  it('should apply a transaction reference only when it is one', () => {
    expect(fieldOf('txRefs')?.validate?.(`0x${'a'.repeat(64)}`)).toBe(true);
    expect(fieldOf('txRefs')?.validate?.('0xnope')).toBe(false);
    expect(fieldOf('txRefs')?.invalidHint).toBe('transactions.filter.invalid_tx_hash');
  });

  it('should apply a validator index only when it is a number', () => {
    expect(fieldOf('validatorIndices')?.validate?.('42')).toBe(true);
    expect(fieldOf('validatorIndices')?.validate?.('0x42')).toBe(false);
  });

  it('should map location values to their display name via resolveLabel', () => {
    expect(fieldOf('location')?.display).toBe('location');
    expect(fieldOf('location')?.resolveLabel?.('polygon_pos')).toBe('name:polygon_pos');
  });
});

describe('toHistoryStateField', () => {
  const states = ['matched', 'customized'];
  const resolveLabel = (value: string): string => `state:${value}`;
  const resolveIcon = (value: string): ValueIcon | undefined =>
    (value === 'matched' ? { color: 'info', icon: 'lu-link' } : undefined);

  it('should build a param-bound state pill field carried on both request and url', () => {
    const field = toHistoryStateField(t, states, resolveLabel, resolveIcon);
    expect(field).toMatchObject({
      binding: { kind: 'param', paramKey: 'stateMarkers', to: 'both' },
      key: 'state',
      label: 'transactions.filter_field_labels.state',
      multiple: true,
      valueType: 'enum',
    });
    expect(field.suggest?.()).toStrictEqual(states);
    expect(field.resolveLabel?.('matched')).toBe('state:matched');
  });

  it('should resolve a per-value icon so the markers keep their glyph and colour', () => {
    const field = toHistoryStateField(t, states, resolveLabel, resolveIcon);
    expect(field.resolveIcon?.('matched')).toStrictEqual({ color: 'info', icon: 'lu-link' });
    expect(field.resolveIcon?.('customized')).toBeUndefined();
  });

  it('should not offer exclusion, which the stateMarkers param cannot express', () => {
    const field = toHistoryStateField(t, states, resolveLabel, resolveIcon);
    expect(field.allowExclusion).toBe(false);
    expect(field.operators).toStrictEqual(['is']);
  });
});

describe('toHistoryActionField', () => {
  const actions = (): { icon: ValueIcon; label: string; verbKey: string }[] => [
    { icon: { color: 'error', icon: 'lu-flame' }, label: 'Pay fee', verbKey: 'pay_fee' },
    { icon: { color: 'success', icon: 'lu-download' }, label: 'Receive', verbKey: 'receive' },
  ];

  // The verb rides the URL alone: the request gets the type/subtype pair from the param source,
  // so rebuilding the pill does not depend on reading raw types back out.
  it('should build a url-only param pill offering the action verbs', () => {
    const field = toHistoryActionField(t, actions);
    expect(field).toMatchObject({
      binding: { kind: 'param', paramKey: 'action', to: 'url' },
      key: 'action',
      label: 'transactions.filter_field_labels.action',
      multiple: false,
    });
    expect(field.suggest?.()).toStrictEqual(['pay_fee', 'receive']);
    expect(field.resolveLabel?.('receive')).toBe('Receive');
    expect(field.resolveIcon?.('pay_fee')).toStrictEqual({ color: 'error', icon: 'lu-flame' });
  });

  it('should fall back to the raw verb when it is no longer offered', () => {
    const field = toHistoryActionField(t, actions);
    expect(field.resolveLabel?.('gone')).toBe('gone');
    expect(field.resolveIcon?.('gone')).toBeUndefined();
  });

  // All three drive the same two request keys, so they must never be active together.
  it('should exclude the type and subtype fields, and be excluded by them', () => {
    expect(toHistoryActionField(t, actions).excludes).toStrictEqual(['eventTypes', 'eventSubtypes']);
    expect(fieldOf('eventTypes')?.excludes).toStrictEqual(['action']);
    expect(fieldOf('eventSubtypes')?.excludes).toStrictEqual(['action']);
  });

  it('should leave unrelated fields with no exclusions', () => {
    expect(fieldOf('counterparties')?.excludes).toBeUndefined();
  });
});

describe('toHistoryIgnoredField', () => {
  // A boolean pill is on once added and off once removed: no editor, no value segment. The wire
  // form stays inverted (`excludeIgnoredAssets`), which the param source handles.
  it('should build a param-bound boolean pill carried on both request and url', () => {
    const field = toHistoryIgnoredField(t);
    expect(field).toMatchObject({
      binding: { kind: 'param', paramKey: 'showIgnoredAssets', to: 'both' },
      key: 'ignored',
      label: 'transactions.filter_field_labels.show_ignored',
      multiple: false,
      valueType: 'boolean',
    });
    expect(field.suggest).toBeUndefined();
    expect(field.operators).toStrictEqual(['is']);
  });
});

describe('toHistoryAccountField', () => {
  it('should build a param-bound account pill field', () => {
    const field = toHistoryAccountField(t, {
      resolveCaption: (address: string): string => `caption:${address}`,
      resolveKeywords: (address: string): string => `${address} alice.eth`,
      resolveLabel: (address: string): string => `label:${address}`,
      resolveLoading: (): boolean => false,
      suggest: (): string[] => ['0xabc', '0xdef'],
    });
    expect(field).toMatchObject({
      binding: { kind: 'param', paramKey: 'locationLabels', to: 'request' },
      display: 'account',
      key: 'account',
      multiple: true,
    });
    expect(field.resolveLabel?.('0xabc')).toBe('label:0xabc');
    expect(field.resolveCaption?.('0xabc')).toBe('caption:0xabc');
  });

  // The bar can only offer an account if the field lists one, and can only find it by address or
  // ENS through the keywords: the label is a name, or a shortened and scrambled address.
  it('should offer its accounts as values, searchable beyond their label', () => {
    const field = toHistoryAccountField(t, {
      resolveCaption: (): undefined => undefined,
      resolveKeywords: (address: string): string => `${address} alice.eth`,
      resolveLabel: (address: string): string => `label:${address}`,
      resolveLoading: (): boolean => false,
      suggest: (): string[] => ['0xabc', '0xdef'],
    });
    expect(field.suggest?.()).toStrictEqual(['0xabc', '0xdef']);
    expect(field.resolveKeywords?.('0xabc')).toBe('0xabc alice.eth');
  });
});
