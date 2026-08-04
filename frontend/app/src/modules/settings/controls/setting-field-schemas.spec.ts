import { describe, expect, it } from 'vitest';
import { numberSettingSchema, textSettingSchema } from '@/modules/settings/controls/setting-field-schemas';

function messagesOf(schema: ReturnType<typeof textSettingSchema>, value: string): string[] {
  const result = schema.safeParse({ value });
  return result.success ? [] : result.error.issues.map(issue => issue.message);
}

describe('textSettingSchema', () => {
  const messages = { maxLength: 'too long', required: 'needed' };

  it('should accept any value when nothing is required', () => {
    expect(messagesOf(textSettingSchema({ messages }), '')).toStrictEqual([]);
  });

  it('should reject a blank value when required', () => {
    const schema = textSettingSchema({ messages, required: true });

    expect(messagesOf(schema, '')).toStrictEqual(['needed']);
    // Vuelidate's `required` trims, so whitespace alone counts as empty.
    expect(messagesOf(schema, '   ')).toStrictEqual(['needed']);
    expect(messagesOf(schema, 'a')).toStrictEqual([]);
  });

  it('should reject a value over the maximum length', () => {
    const schema = textSettingSchema({ maxLength: 3, messages });

    expect(messagesOf(schema, 'abcd')).toStrictEqual(['too long']);
    expect(messagesOf(schema, 'abc')).toStrictEqual([]);
  });

  it('should not report a length error for an optional blank value', () => {
    // Reporting both would show "too long" on an empty field the user never has to fill in.
    expect(messagesOf(textSettingSchema({ maxLength: 3, messages }), '')).toStrictEqual([]);
  });
});

describe('numberSettingSchema', () => {
  const messages = { between: 'out of range', max: 'too big', min: 'too small', required: 'needed' };

  it('should reject a blank value by default', () => {
    expect(messagesOf(numberSettingSchema({ messages }), '')).toStrictEqual(['needed']);
  });

  it('should accept a blank value when not required', () => {
    expect(messagesOf(numberSettingSchema({ messages, required: false }), '')).toStrictEqual([]);
  });

  it('should reject a value below the minimum', () => {
    const schema = numberSettingSchema({ messages, min: 2 });

    expect(messagesOf(schema, '1')).toStrictEqual(['too small']);
    expect(messagesOf(schema, '2')).toStrictEqual([]);
  });

  it('should reject a value above the maximum', () => {
    const schema = numberSettingSchema({ max: 5, messages });

    expect(messagesOf(schema, '6')).toStrictEqual(['too big']);
    expect(messagesOf(schema, '5')).toStrictEqual([]);
  });

  it('should report the between message when both bounds are given', () => {
    // One message rather than two: the field says "between 2 and 5", not "too small" and "too big".
    const schema = numberSettingSchema({ max: 5, messages, min: 2 });

    expect(messagesOf(schema, '1')).toStrictEqual(['out of range']);
    expect(messagesOf(schema, '6')).toStrictEqual(['out of range']);
    expect(messagesOf(schema, '3')).toStrictEqual([]);
  });

  it('should reject a value that is not a number', () => {
    expect(messagesOf(numberSettingSchema({ messages, min: 1 }), 'abc')).toStrictEqual(['needed']);
  });
});
