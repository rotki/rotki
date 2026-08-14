import { describe, expect, it } from 'vitest';
import { customAssetSchema } from '@/modules/assets/admin/custom/custom-asset-form';

const messages = {
  customAssetType: 'type_missing',
  name: 'name_missing',
};

const valid = {
  customAssetType: 'real estate',
  identifier: 'custom-1',
  name: 'A house',
  notes: 'bought in 2019',
};

function messagesFor(state: Record<string, unknown>): string[] {
  const result = customAssetSchema(messages).safeParse(state);
  if (result.success)
    return [];
  return result.error.issues.map(issue => issue.message);
}

describe('customAssetSchema', () => {
  it('should accept a filled asset', () => {
    expect(messagesFor(valid)).toEqual([]);
  });

  it.each([
    ['customAssetType', 'type_missing'],
    ['name', 'name_missing'],
  ])('should report %s under its own message when empty', (key, message) => {
    expect(messagesFor({ ...valid, [key]: '' })).toEqual([message]);
  });

  it('should treat a whitespace-only name as empty', () => {
    expect(messagesFor({ ...valid, name: '  ' })).toEqual(['name_missing']);
  });

  it('should accept an asset with no notes', () => {
    expect(messagesFor({ ...valid, notes: null })).toEqual([]);
  });

  it('should carry the fields it does not validate', () => {
    const result = customAssetSchema(messages).safeParse(valid);

    // Notes and the identifier reach the api untouched. Rejecting them here would block the save
    // with nothing on screen, since neither has a message bound to it.
    expect(result.success && result.data).toEqual(valid);
  });

  it('should report both empty fields rather than stopping at the first', () => {
    expect(messagesFor({ ...valid, customAssetType: '', name: '' })).toEqual([
      'type_missing',
      'name_missing',
    ]);
  });
});
