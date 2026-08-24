import { bigNumberify, Zero } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { ref } from 'vue';
import { bigNumberifyFromRef, parseNumericInput, sortDesc, zeroBalance } from '@/modules/core/common/data/bignumbers';

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

  describe('parseNumericInput', () => {
    it('should parse a numeric string', () => {
      expect(parseNumericInput('1.5')?.toFixed()).toBe('1.5');
    });

    it('should parse a number', () => {
      expect(parseNumericInput(2)?.toFixed()).toBe('2');
    });

    it('should keep zero apart from nothing typed', () => {
      expect(parseNumericInput('0')).toStrictEqual(Zero);
      expect(parseNumericInput('')).toBeUndefined();
      expect(parseNumericInput('   ')).toBeUndefined();
    });

    // The first group throws in bignumber.js, the second parses into something unusable. A caller
    // that has to reject a value cannot tell them apart, so neither may come back as a number.
    it.each(['abc', '1.2.3', '-', '.', '0,5', '1 000'])('should reject %s, which throws', (input) => {
      expect(() => bigNumberify(input)).toThrow();
      expect(parseNumericInput(input)).toBeUndefined();
    });

    it.each(['NaN', 'Infinity', '-Infinity'])('should reject %s, which parses', (input) => {
      expect(() => bigNumberify(input)).not.toThrow();
      expect(parseNumericInput(input)).toBeUndefined();
    });

    it('should accept a partially typed decimal', () => {
      expect(parseNumericInput('1.')?.toFixed()).toBe('1');
      expect(parseNumericInput('.5')?.toFixed()).toBe('0.5');
    });

    // With a fallback the result is a number the caller can use straight away, so the parse and the
    // "what does an unreadable field mean here" decision stay in one place.
    it.each(['', '-', '1.2.3', 'NaN'])('should fall back on %s when given a fallback', (input) => {
      expect(parseNumericInput(input, Zero)).toStrictEqual(Zero);
    });

    it('should ignore the fallback when the value reads', () => {
      expect(parseNumericInput('1.5', Zero).toFixed()).toBe('1.5');
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
