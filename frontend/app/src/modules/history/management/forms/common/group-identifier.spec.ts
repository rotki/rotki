import { describe, expect, it } from 'vitest';
import {
  groupIdentifierFields,
  groupIdentifierSchema,
  toNullableText,
} from '@/modules/history/management/forms/common/group-identifier';

describe('groupIdentifierFields', () => {
  it('should use the event\'s own identifier when it was not linked', () => {
    expect(groupIdentifierFields({ groupIdentifier: 'OWN' })).toEqual({
      groupIdentifier: 'OWN',
      hasActualGroupIdentifier: false,
    });
  });

  it('should prefer the linked identifier and lock the field', () => {
    const fields = groupIdentifierFields({ actualGroupIdentifier: 'LINKED', groupIdentifier: 'OWN' });

    expect(fields).toEqual({ groupIdentifier: 'LINKED', hasActualGroupIdentifier: true });
  });

  it('should treat a blank linked identifier as no link', () => {
    for (const actual of ['', null, undefined]) {
      expect(groupIdentifierFields({ actualGroupIdentifier: actual, groupIdentifier: 'OWN' })).toEqual({
        groupIdentifier: 'OWN',
        hasActualGroupIdentifier: false,
      });
    }
  });
});

describe('toNullableText', () => {
  it('should send null rather than an empty string', () => {
    expect(toNullableText('')).toBeNull();
    expect(toNullableText('value')).toBe('value');
  });
});

describe('groupIdentifierSchema', () => {
  it('should accept a blank identifier while adding', () => {
    expect(groupIdentifierSchema(false).safeParse('').success).toBe(true);
  });

  it('should require one while editing', () => {
    expect(groupIdentifierSchema(true).safeParse('').success).toBe(false);
    expect(groupIdentifierSchema(true).safeParse('OWN').success).toBe(true);
  });
});
