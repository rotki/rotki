import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { WORD_PROCESSORS, type WordProcessorContext } from './note-processors';

function createContext(word: string, overrides: Partial<WordProcessorContext> = {}): WordProcessorContext {
  return {
    amountArr: [bigNumberify(100)],
    getAssetSymbol: (id: string): string => id,
    getCleanWord: (value: string): string => value,
    index: 0,
    processedWords: [word],
    shouldFormatAllAmount: false,
    validatorIndices: [],
    word,
    ...overrides,
  };
}

const AMOUNTS_MATCHING_A_NUMERIC_PREFIX = [bigNumberify(9), bigNumberify(15)];

describe('note word processors', () => {
  it.each([
    '09/09/2026',
    '1/2/2027',
    '2026-09-09',
    '15:04:56',
    '12:30',
    '0x1234zz',
    '1.2.3',
    '-',
    '.',
  ])('should not throw on the non-numeric word "%s"', (word) => {
    for (const processor of WORD_PROCESSORS)
      expect(() => processor(createContext(word))).not.toThrow();
  });

  it.each([
    '09/09/2026',
    '1/2/2027',
    '2026-09-09',
    '15:04:56',
    '12:30',
  ])('should not treat the date or time "%s" as an amount', (word) => {
    const results = WORD_PROCESSORS
      .map(processor => processor(createContext(word, { amountArr: AMOUNTS_MATCHING_A_NUMERIC_PREFIX })))
      .filter(Boolean);

    expect(results).toHaveLength(0);
  });

  it('should not throw on a non-numeric word when every amount is formatted', () => {
    for (const processor of WORD_PROCESSORS)
      expect(() => processor(createContext('09/09/2026', { shouldFormatAllAmount: true }))).not.toThrow();
  });

  it('should still recognise a genuine amount', () => {
    const results = WORD_PROCESSORS.map(processor => processor(createContext('100'))).filter(Boolean);

    expect(results).toHaveLength(1);
    expect(results[0]?.format).toMatchObject({ amount: bigNumberify(100) });
  });

  it('should still recognise an amount written with thousand separators', () => {
    const ctx = createContext('15,123.233', { amountArr: [bigNumberify(15123.233)] });
    const results = WORD_PROCESSORS.map(processor => processor(ctx)).filter(Boolean);

    expect(results).toHaveLength(1);
    expect(results[0]?.format).toMatchObject({ amount: bigNumberify(15123.233) });
  });
});
