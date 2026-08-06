import { describe, expect, it } from 'vitest';
import { type NumericSeparatorsMessages, numericSeparatorsSchema } from '@/modules/settings/general/amount/numeric-separators';

const messages: NumericSeparatorsMessages = {
  decimal: {
    empty: 'decimal.empty',
    numeric: 'decimal.numeric',
    sameAsOther: 'decimal.same',
    singleCharacter: 'decimal.single',
  },
  thousand: {
    empty: 'thousand.empty',
    numeric: 'thousand.numeric',
    sameAsOther: 'thousand.same',
    singleCharacter: 'thousand.single',
  },
};

function messagesFor(thousand: string, decimal: string): Record<string, string[]> {
  const result = numericSeparatorsSchema(messages).safeParse({ decimal, thousand });
  if (result.success)
    return {};

  const map: Record<string, string[]> = {};
  for (const issue of result.error.issues)
    (map[issue.path.join('.')] ??= []).push(issue.message);

  return map;
}

describe('numericSeparatorsSchema', () => {
  it('should accept two different single characters', () => {
    expect(messagesFor(',', '.')).toStrictEqual({});
  });

  it('should accept a space as a separator', () => {
    expect(messagesFor(' ', '.')).toStrictEqual({});
  });

  it('should accept a multi-code-point emoji as one visual character', () => {
    expect(messagesFor('👩‍💻', '.')).toStrictEqual({});
  });

  it('should reject a digit', () => {
    expect(messagesFor('1', '.').thousand).toStrictEqual(['thousand.numeric']);
  });

  it('should reject an empty separator with both the empty and the length message', () => {
    expect(messagesFor('', '.').thousand).toStrictEqual(['thousand.empty', 'thousand.single']);
  });

  it('should reject more than one visual character', () => {
    expect(messagesFor('..', ',').thousand).toStrictEqual(['thousand.single']);
  });

  it('should report an equal pair on both fields', () => {
    expect(messagesFor(',', ',')).toStrictEqual({
      decimal: ['decimal.same'],
      thousand: ['thousand.same'],
    });
  });

  it('should keep each field messages under its own path', () => {
    const result = messagesFor('1', '..');
    expect(result.thousand).toStrictEqual(['thousand.numeric']);
    expect(result.decimal).toStrictEqual(['decimal.single']);
  });
});
