import { bigNumberify, Zero } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { ref } from 'vue';
import { bigNumberifyFromRef, sortDesc, zeroBalance } from '@/modules/core/common/data/bignumbers';

describe('core/common/data/bignumbers', () => {
  describe('bigNumberifyFromRef', () => {
    it('should parse a numeric string', () => {
      const value = bigNumberifyFromRef(ref('1.5'));
      expect(value.value.toFixed()).toBe('1.5');
    });

    it('should track the ref it was built from', () => {
      const source = ref('2');
      const value = bigNumberifyFromRef(source);
      expect(value.value.toFixed()).toBe('2');

      source.value = '3';
      expect(value.value.toFixed()).toBe('3');
    });

    it('should read a cleared field as zero', () => {
      const value = bigNumberifyFromRef(ref(''));
      expect(value.value).toStrictEqual(Zero);
    });

    // These are the values bignumber.js throws on. The helper runs inside a computed, so a throw
    // here is a render-time exception in whichever form is bound to the field.
    it.each(['abc', '1.2.3', '-', '.', '0,5', '1 000'])('should read %s as zero rather than throw', (input) => {
      expect(() => bigNumberify(input)).toThrow();

      const value = bigNumberifyFromRef(ref(input));
      expect(value.value).toStrictEqual(Zero);
    });
  });

  describe('zeroBalance', () => {
    it('should build a balance of zeroes', () => {
      expect(zeroBalance()).toStrictEqual({ amount: Zero, value: Zero });
    });
  });

  describe('sortDesc', () => {
    it('should order the larger value first', () => {
      const values = [bigNumberify('1'), bigNumberify('3'), bigNumberify('2')];
      expect(values.sort(sortDesc).map(value => value.toFixed())).toEqual(['3', '2', '1']);
    });
  });
});
