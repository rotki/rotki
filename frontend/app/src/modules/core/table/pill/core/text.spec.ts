import { describe, expect, it } from 'vitest';
import { resolveOptionalText, resolveText } from '@/modules/core/table/pill/core/text';

describe('resolveText', () => {
  it('should pass a finished string through', () => {
    expect(resolveText('Asset')).toBe('Asset');
  });

  it('should call a getter', () => {
    expect(resolveText(() => 'Asset')).toBe('Asset');
  });

  // The whole point of the getter: a field can be built once and still follow the locale, because
  // the call happens where the bar draws it rather than where the field was declared.
  it('should call the getter every time rather than caching it', () => {
    let locale = 'en';
    const label = (): string => (locale === 'en' ? 'Asset' : 'Anlage');

    expect(resolveText(label)).toBe('Asset');
    locale = 'de';
    expect(resolveText(label)).toBe('Anlage');
  });

  // An empty label is a label; only `undefined` means the field omitted the copy.
  it('should keep an empty string', () => {
    expect(resolveText('')).toBe('');
    expect(resolveText(() => '')).toBe('');
  });
});

describe('resolveOptionalText', () => {
  it('should resolve copy a field did supply', () => {
    expect(resolveOptionalText('hint')).toBe('hint');
    expect(resolveOptionalText(() => 'hint')).toBe('hint');
  });

  // The editors fall back to their generic message on undefined, so it must survive as undefined
  // rather than becoming an empty string that reads as a supplied blank.
  it('should leave omitted copy undefined', () => {
    expect(resolveOptionalText(undefined)).toBeUndefined();
  });
});
