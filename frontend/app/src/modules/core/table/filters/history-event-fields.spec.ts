import type { AssetsWithId } from '@/modules/assets/types';
import type { ValueIcon } from '@/modules/core/table/pill/core/types';
import { describe, expect, it } from 'vitest';
import { toHistoryAccountField, toHistoryActionField, toHistoryEventFields, toHistoryIgnoredField, toHistoryStateField } from '@/modules/core/table/filters/history-event-fields';
import { HistoryEventFilterKeys, HistoryEventFilterValueKeys, type Matcher } from '@/modules/core/table/filters/use-events-filter';

const t = (key: string): string => key;
const resolvers = {
  formatDate: (value: string): string => `date:${value}`,
  // The real one reads the user's date format; here anything with two slashes is a date, so the
  // parsing rules stay the parser's own tests and these stay about field assembly.
  parseDate: (value: string): string | undefined => (/^\d+\/\d+\/\d+$/.test(value) ? `ts:${value}` : undefined),
  resolveHex: (value: string): string => `hex:${value}`,
  resolveAssetChain: (value: string): string | undefined => (value.startsWith('eip155:8453') ? 'base' : undefined),
  resolveAssetSymbol: (value: string): string => `symbol:${value}`,
  resolveEventSubTypeName: (value: string): string => `subtype:${value}`,
  resolveEventTypeName: (value: string): string => `type:${value}`,
  resolveLocationName: (value: string): string => `name:${value}`,
  resolveProtocolName: (value: string): string => `protocol:${value}`,
  resolveTokenName: (value: string): string => `entry:${value}`,
  t,
};

function stringMatcher(key: HistoryEventFilterKeys, keyValue: HistoryEventFilterValueKeys): Matcher {
  return {
    description: `filter by ${key}`,
    key,
    keyValue,
    string: true,
    suggestions: (): string[] => [],
    validate: (): boolean => true,
  };
}

describe('toHistoryEventFields', () => {
  it('should collapse the two amount matchers into one range field', () => {
    const matchers = [
      stringMatcher(HistoryEventFilterKeys.MIN_AMOUNT, HistoryEventFilterValueKeys.MIN_AMOUNT),
      stringMatcher(HistoryEventFilterKeys.MAX_AMOUNT, HistoryEventFilterValueKeys.MAX_AMOUNT),
    ];
    const fields = toHistoryEventFields(matchers, resolvers);
    expect(fields).toHaveLength(1);
    expect(fields[0]).toMatchObject({
      bounds: { lower: 'minAmount', upper: 'maxAmount' },
      key: 'amount',
      label: 'transactions.filter_field_labels.amount',
      valueType: 'range',
    });
  });

  it('should collapse the two period matchers into one date field', () => {
    const matchers = [
      stringMatcher(HistoryEventFilterKeys.START, HistoryEventFilterValueKeys.START),
      stringMatcher(HistoryEventFilterKeys.END, HistoryEventFilterValueKeys.END),
    ];
    const fields = toHistoryEventFields(matchers, resolvers);
    expect(fields).toHaveLength(1);
    expect(fields[0]).toMatchObject({
      bounds: { lower: 'fromTimestamp', upper: 'toTimestamp' },
      key: 'period',
      valueType: 'date',
    });
  });

  it('should give a matcher field its short pill label', () => {
    const fields = toHistoryEventFields(
      [stringMatcher(HistoryEventFilterKeys.PROTOCOL, HistoryEventFilterValueKeys.PROTOCOL)],
      resolvers,
    );
    expect(fields[0].label).toBe('transactions.filter_field_labels.protocol');
    expect(fields[0].key).toBe('counterparties');
  });

  it('should keep an unmapped field label as the matcher description', () => {
    const notes = stringMatcher(HistoryEventFilterKeys.NOTES, HistoryEventFilterValueKeys.NOTES);
    const fields = toHistoryEventFields([{ ...notes, keyValue: undefined }], resolvers);
    expect(fields[0].label).toBe('filter by notes');
  });

  it('should resolve the chain of an asset value, and only for the asset field', () => {
    const [assetField] = toHistoryEventFields(
      [{ asset: true, description: 'filter by asset', key: HistoryEventFilterKeys.ASSET, keyValue: HistoryEventFilterValueKeys.ASSET, suggestions: async (): Promise<AssetsWithId> => [] }],
      resolvers,
    );
    const [locationField] = toHistoryEventFields(
      [stringMatcher(HistoryEventFilterKeys.LOCATION, HistoryEventFilterValueKeys.LOCATION)],
      resolvers,
    );

    expect(assetField.resolveChain?.('eip155:8453/erc20:0x8Fa0')).toBe('base');
    expect(assetField.resolveChain?.('BTC')).toBeUndefined();
    expect(locationField.resolveChain).toBeUndefined();
  });

  it('should map event type, subtype and entry type values to their display name', () => {
    const [eventType] = toHistoryEventFields(
      [stringMatcher(HistoryEventFilterKeys.EVENT_TYPE, HistoryEventFilterValueKeys.EVENT_TYPE)],
      resolvers,
    );
    const [subtype] = toHistoryEventFields(
      [stringMatcher(HistoryEventFilterKeys.EVENT_SUBTYPE, HistoryEventFilterValueKeys.EVENT_SUBTYPE)],
      resolvers,
    );

    expect(eventType.resolveLabel?.('informational')).toBe('type:informational');
    expect(subtype.resolveLabel?.('receive_wrapped')).toBe('subtype:receive_wrapped');
  });

  it('should map address values through the address resolver', () => {
    const [addresses] = toHistoryEventFields(
      [stringMatcher(HistoryEventFilterKeys.ADDRESSES, HistoryEventFilterValueKeys.ADDRESSES)],
      resolvers,
    );

    expect(addresses.resolveLabel?.('0xabc')).toBe('hex:0xabc');
  });

  // A full hash is both too long for a pill and, in privacy mode, as revealing as an address.
  it('should shorten and scramble tx hash values like addresses', () => {
    const [txHashes] = toHistoryEventFields(
      [stringMatcher(HistoryEventFilterKeys.TX_HASHES, HistoryEventFilterValueKeys.TX_HASHES)],
      resolvers,
    );

    expect(txHashes.resolveLabel?.('0xdeadbeef')).toBe('hex:0xdeadbeef');
  });

  it('should map location values to their display name via resolveLabel', () => {
    const fields = toHistoryEventFields(
      [stringMatcher(HistoryEventFilterKeys.LOCATION, HistoryEventFilterValueKeys.LOCATION)],
      resolvers,
    );
    expect(fields[0].display).toBe('location');
    expect(fields[0].resolveLabel?.('polygon_pos')).toBe('name:polygon_pos');
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
    const field = toHistoryActionField(t, actions);
    expect(field.excludes).toStrictEqual(['eventTypes', 'eventSubtypes']);

    const [eventType] = toHistoryEventFields(
      [stringMatcher(HistoryEventFilterKeys.EVENT_TYPE, HistoryEventFilterValueKeys.EVENT_TYPE)],
      resolvers,
    );
    const [subtype] = toHistoryEventFields(
      [stringMatcher(HistoryEventFilterKeys.EVENT_SUBTYPE, HistoryEventFilterValueKeys.EVENT_SUBTYPE)],
      resolvers,
    );
    expect(eventType.excludes).toStrictEqual(['action']);
    expect(subtype.excludes).toStrictEqual(['action']);
  });

  it('should leave unrelated fields with no exclusions', () => {
    const [protocol] = toHistoryEventFields(
      [stringMatcher(HistoryEventFilterKeys.PROTOCOL, HistoryEventFilterValueKeys.PROTOCOL)],
      resolvers,
    );
    expect(protocol.excludes).toBeUndefined();
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
      suggest: (): string[] => ['0xabc', '0xdef'],
    });
    expect(field.suggest?.()).toStrictEqual(['0xabc', '0xdef']);
    expect(field.resolveKeywords?.('0xabc')).toBe('0xabc alice.eth');
  });
});
