import { describe, expect, it } from 'vitest';
import { resolveOptionalText, resolveText } from '@/modules/core/table/pill/core/text';

describe('resolveText', () => {
  it('should pass a finished string through', () => {
    expect(resolveText('Asset')).toBe('Asset');
  });

  it('should call a getter', () => {
    expect(resolveText(() => 'Asset')).toBe('Asset');
  });

  it('should call the getter every time rather than caching it, so a field built once still follows the locale', () => {
    let locale = 'en';
    const label = (): string => (locale === 'en' ? 'Asset' : 'Anlage');

    expect(resolveText(label)).toBe('Asset');
    locale = 'de';
    expect(resolveText(label)).toBe('Anlage');
  });

  it('should keep an empty string, only `undefined` meaning the field omitted the copy', () => {
    expect(resolveText('')).toBe('');
    expect(resolveText(() => '')).toBe('');
  });
});

describe('resolveOptionalText', () => {
  it('should resolve copy a field did supply', () => {
    expect(resolveOptionalText('hint')).toBe('hint');
    expect(resolveOptionalText(() => 'hint')).toBe('hint');
  });

  it('should leave omitted copy undefined rather than an empty string, so an editor still falls back to its generic message', () => {
    expect(resolveOptionalText(undefined)).toBeUndefined();
  });
});
