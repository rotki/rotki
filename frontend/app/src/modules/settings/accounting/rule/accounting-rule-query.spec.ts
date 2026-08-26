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

  // The url is the user's to write, and an unrecognised handling would be sent to the backend as a
  // filter it refuses.
  it('should refuse anything else', () => {
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

  // The link is written by other pages, so a half-written one still has to open the form.
  it('should default what a link leaves out', () => {
    expect(parseRuleQuery({ eventType: 'spend' })).toStrictEqual({
      counterparty: null,
      eventSubtype: '',
      eventType: 'spend',
    });
  });

  it('should default an empty query rather than throw', () => {
    expect(parseRuleQuery({})).toStrictEqual({ counterparty: null, eventSubtype: '', eventType: '' });
  });

  // A repeated parameter arrives as an array, which is neither a rule identity nor something the
  // form can use. Passing it through reached zod as an array and threw, taking the whole page down.
  it('should ignore a repeated parameter', () => {
    expect(parseRuleQuery({ eventType: ['spend', 'receive'] })).toStrictEqual({
      counterparty: null,
      eventSubtype: '',
      eventType: '',
    });
  });

  // vue-router parses a valueless parameter as null, and a `z.string()` default only covers
  // undefined. Passing it through threw an invalid_type error from inside onMounted, which took
  // the rest of the page's setup with it and left the table empty for the session.
  it('should default a parameter written with no value', () => {
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

  // Identifiers start at 1, and `Number(' ')` is a finite 0, so a range check is not enough.
  it('should read nothing for an id no event can have', () => {
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

  // Both at once is a link that cannot be honoured twice; adding is the safer of the two, since
  // editing needs a rule that may not exist.
  it('should prefer adding when a link asks for both', () => {
    expect(parseRuleIntent({ 'add-rule': 'true', 'edit-rule': 'true' })).toBe('add');
  });
});
