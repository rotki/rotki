import { describe, expect, it } from 'vitest';
import { dateFormatSchema } from '@/modules/settings/general/date-format-schema';

const schema = dateFormatSchema({ empty: 'empty', invalid: 'invalid' });

function messagesFor(value: string): string[] {
  const result = schema.safeParse({ value });
  return result.success ? [] : result.error.issues.map(issue => issue.message);
}

describe('dateFormatSchema', () => {
  it('should accept a pattern with a valid directive', () => {
    expect(messagesFor('%d/%m/%Y %H:%M:%S')).toStrictEqual([]);
  });

  it('should accept a pattern whose only directive is valid', () => {
    expect(messagesFor('%Y')).toStrictEqual([]);
  });

  it('should reject a pattern with no directives', () => {
    expect(messagesFor('not a format')).toStrictEqual(['invalid']);
  });

  it('should reject a blank pattern with both messages', () => {
    expect(messagesFor('')).toStrictEqual(['invalid', 'empty']);
  });
});
