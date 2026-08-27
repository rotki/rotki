import { describe, expect, it } from 'vitest';
import { type EventTypeSubtypeMapping, subtypesForTypes } from '@/modules/history/events/mapping/event-type-subtypes';

const mapping: EventTypeSubtypeMapping = {
  receive: { 'airdrop': {}, 'return wrapped': {} },
  spend: { 'fee': {}, 'return wrapped': {} },
};

describe('subtypesForTypes', () => {
  it('should offer the subtypes of the selected type', () => {
    expect(subtypesForTypes(mapping, ['spend'])).toStrictEqual(['fee', 'return wrapped']);
  });

  it('should union the subtypes across several types, without repeating one', () => {
    expect(subtypesForTypes(mapping, ['spend', 'receive']))
      .toStrictEqual(['fee', 'return wrapped', 'airdrop']);
  });

  it('should offer every known subtype when no type is picked', () => {
    expect(subtypesForTypes(mapping, [])).toStrictEqual(['airdrop', 'return wrapped', 'fee']);
  });

  it('should offer nothing for a type the mapping does not know', () => {
    expect(subtypesForTypes(mapping, ['nonsense'])).toStrictEqual([]);
  });

  it('should offer nothing while the mapping is empty, which callers read as "not known yet" rather than "this type admits nothing"', () => {
    expect(subtypesForTypes({}, ['spend'])).toStrictEqual([]);
  });
});
