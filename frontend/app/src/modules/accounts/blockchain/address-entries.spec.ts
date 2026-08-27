import { describe, expect, it } from 'vitest';
import {
  addressEntrySchema,
  isXpubPrefix,
  parseAddressEntries,
  replaceSelection,
} from '@/modules/accounts/blockchain/address-entries';

const ADDRESS = '0x9531C059098e3d194fF87FebB587aB07B30B1306';
const OTHER_ADDRESS = '0xc37b40ABdB939635068d3c5f13E7faF686F03B65';
const MESSAGE = 'an address is required';

describe('modules/accounts/blockchain/address-entries', () => {
  describe('parseAddressEntries', () => {
    it('should read an empty list as no addresses', () => {
      expect(parseAddressEntries('')).toEqual([]);
      expect(parseAddressEntries('  \n , ')).toEqual([]);
    });

    it.each([
      ['a comma', `${ADDRESS},${OTHER_ADDRESS}`],
      ['a newline', `${ADDRESS}\n${OTHER_ADDRESS}`],
      ['both', `${ADDRESS},\n${OTHER_ADDRESS}`],
      ['surrounding space', `  ${ADDRESS} ,  ${OTHER_ADDRESS}  `],
    ])('should split on %s', (_label, text) => {
      expect(parseAddressEntries(text)).toEqual([ADDRESS, OTHER_ADDRESS]);
    });

    it('should keep the first spelling of a repeated address, the same account in another case', () => {
      expect(parseAddressEntries(`${ADDRESS}\n${ADDRESS.toLowerCase()}`)).toEqual([ADDRESS]);
    });

    it('should keep the order the addresses were written in', () => {
      expect(parseAddressEntries(`${OTHER_ADDRESS},${ADDRESS}`)).toEqual([OTHER_ADDRESS, ADDRESS]);
    });
  });

  describe('isXpubPrefix', () => {
    it.each([
      ['xpub6CUGRUon', true],
      ['ypub6Ww3ibxVfGz', true],
      ['zpub6rFR7y4Q2Aij', true],
      [ADDRESS, false],
      ['', false],
    ])('should read "%s" as an extended key: %s', (value, expected) => {
      expect(isXpubPrefix(value)).toBe(expected);
    });
  });

  describe('replaceSelection', () => {
    it('should substitute the selected range', () => {
      expect(replaceSelection('one,two', 'four', 4, 7)).toBe('one,four');
    });

    it('should insert at a caret with nothing selected', () => {
      expect(replaceSelection('one,', 'two', 4, 4)).toBe('one,two');
    });
  });

  describe('addressEntrySchema', () => {
    function messagesFor(state: { address: string; userAddresses: string }, multiple: boolean): string[] {
      const result = addressEntrySchema(MESSAGE, multiple).safeParse(state);
      if (result.success)
        return [];
      return result.error.issues.map(issue => `${issue.path.join('.')}: ${issue.message}`);
    }

    it('should require the single address while one is being entered', () => {
      expect(messagesFor({ address: '', userAddresses: '' }, false)).toEqual([`address: ${MESSAGE}`]);
      expect(messagesFor({ address: ADDRESS, userAddresses: '' }, false)).toEqual([]);
    });

    it('should require the list while several are being entered', () => {
      expect(messagesFor({ address: '', userAddresses: '' }, true)).toEqual([`userAddresses: ${MESSAGE}`]);
      expect(messagesFor({ address: '', userAddresses: ADDRESS }, true)).toEqual([]);
    });

    it('should ignore the field that is not on screen', () => {
      // Only one of the two is ever shown, so an empty other field is not something to report.
      expect(messagesFor({ address: ADDRESS, userAddresses: '' }, false)).toEqual([]);
      expect(messagesFor({ address: '', userAddresses: ADDRESS }, true)).toEqual([]);
    });

    it.each([
      ['one address', false],
      ['several', true],
    ])('should treat whitespace as missing when entering %s', (_label, multiple) => {
      expect(messagesFor({ address: '   ', userAddresses: '   ' }, multiple)).toHaveLength(1);
    });
  });
});
