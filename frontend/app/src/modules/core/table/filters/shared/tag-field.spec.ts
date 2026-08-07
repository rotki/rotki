import { describe, expect, it } from 'vitest';
import { type TagFieldOption, toTagsField } from '@/modules/core/table/filters/shared/tag-field';

const t = (key: string): string => key;

const tags: TagFieldOption[] = [
  { name: 'office', swatch: { background: '#ffffff', foreground: '#000000' } },
];

describe('toTagsField', () => {
  it('should bind the tags field to the tags param', () => {
    expect(toTagsField(t, () => tags)).toMatchObject({
      binding: { kind: 'param', paramKey: 'tags', to: 'both' },
      key: 'tags',
      label: 'common.tags',
      multiple: true,
    });
  });

  it('should offer every tag as a value', () => {
    expect(toTagsField(t, () => tags).suggest?.()).toStrictEqual(['office']);
  });

  it('should resolve a tag to the colours it is recognised by', () => {
    const field = toTagsField(t, () => tags);

    expect(field.resolveSwatch?.('office')).toStrictEqual({ background: '#ffffff', foreground: '#000000' });
    expect(field.resolveSwatch?.('unknown')).toBeUndefined();
  });
});
