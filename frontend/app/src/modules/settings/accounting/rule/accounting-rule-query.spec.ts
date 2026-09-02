import { describe, expect, it } from 'vitest';
import {
  AccountingRuleQuerySchema,
  CustomRuleHandling,
  isCustomRuleHandling,
  parseEventId,
  parseRuleIntent,
  parseRuleQuery,
} from '@/modules/settings/accounting/rule/accounting-rule-query';

describe('isCustomRuleHandling', () => {
  it('should admit the two handlings the tabs send', () => {
    expect(isCustomRuleHandling(CustomRuleHandling.EXCLUDE)).toBe(true);
    expect(isCustomRuleHandling(CustomRuleHandling.ONLY)).toBe(true);
  });

  it('should refuse a handling the backend would not accept as a filter', () => {
    expect(isCustomRuleHandling('all')).toBe(false);
    expect(isCustomRuleHandling('')).toBe(false);
    expect(isCustomRuleHandling('ONLY')).toBe(false);
  });
});

describe('parseRuleQuery', () => {
  it('should read the rule a deep link names', () => {
    expect(parseRuleQuery({ counterparty: 'uniswap-v2', eventSubtype: 'fee', eventType: 'spend' })).toStrictEqual({
      counterparty: 'uniswap-v2',
      eventSubtype: 'fee',
      eventType: 'spend',
    });
  });

  it('should default what a link leaves out, so a half-written one still opens the form', () => {
    expect(parseRuleQuery({ eventType: 'spend' })).toStrictEqual({
      counterparty: null,
      eventSubtype: '',
      eventType: 'spend',
    });
  });

  it('should default an empty query rather than throw', () => {
    expect(parseRuleQuery({})).toStrictEqual({ counterparty: null, eventSubtype: '', eventType: '' });
  });

  it('should ignore a repeated parameter, which arrives as an array', () => {
    expect(parseRuleQuery({ eventType: ['spend', 'receive'] })).toStrictEqual({
      counterparty: null,
      eventSubtype: '',
      eventType: '',
    });
  });

  it('should default a parameter written with no value, which vue-router parses as null', () => {
    expect(parseRuleQuery({ eventSubtype: null, eventType: null })).toStrictEqual({
      counterparty: null,
      eventSubtype: '',
      eventType: '',
    });
  });

  it('should keep a null counterparty, which is the wire form for "any"', () => {
    expect(AccountingRuleQuerySchema.parse({ counterparty: null })).toStrictEqual({
      counterparty: null,
      eventSubtype: '',
      eventType: '',
    });
  });
});

describe('parseEventId', () => {
  it('should read the event a link points at', () => {
    expect(parseEventId({ eventId: '42' })).toBe(42);
  });

  it('should read nothing when the link names no event', () => {
    expect(parseEventId({})).toBeUndefined();
    expect(parseEventId({ eventId: '' })).toBeUndefined();
  });

  it('should read nothing when the link names nonsense, rather than passing on NaN', () => {
    expect(parseEventId({ eventId: 'abc' })).toBeUndefined();
    expect(parseEventId({ eventId: ['1', '2'] })).toBeUndefined();
  });

  it('should read nothing for an id no event can have, identifiers starting at 1', () => {
    expect(parseEventId({ eventId: '0' })).toBeUndefined();
    expect(parseEventId({ eventId: ' ' })).toBeUndefined();
    expect(parseEventId({ eventId: '-3' })).toBeUndefined();
  });
});

describe('parseRuleIntent', () => {
  it('should read which intent a route carries', () => {
    expect(parseRuleIntent({ 'add-rule': 'true' })).toBe('add');
    expect(parseRuleIntent({ 'edit-rule': 'true' })).toBe('edit');
    expect(parseRuleIntent({})).toBeUndefined();
  });

  it('should prefer adding when a link asks for both, since editing needs a rule that may not exist', () => {
    expect(parseRuleIntent({ 'add-rule': 'true', 'edit-rule': 'true' })).toBe('add');
  });
});
