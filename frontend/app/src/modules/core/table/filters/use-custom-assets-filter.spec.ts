import { assert, describe, expect, it, vi } from 'vitest';
import { useCustomAssetFilter } from '@/modules/core/table/filters/use-custom-assets-filter';

vi.mock('vue-i18n', async importOriginal => ({
  ...await importOriginal<typeof import('vue-i18n')>(),
  useI18n: (): { t: (key: string) => string } => ({ t: (key: string): string => key }),
}));

describe('useCustomAssetFilter', () => {
  it('should start with an empty filter', () => {
    const { filters } = useCustomAssetFilter([]);
    expect(get(filters)).toEqual({});
  });

  it('should expose matchers for name and type', () => {
    const { matchers } = useCustomAssetFilter([]);
    const keys = get(matchers).map(matcher => matcher.key);
    expect(keys).toEqual(['name', 'type']);
  });

  it('should surface the provided type suggestions', () => {
    const { matchers } = useCustomAssetFilter(['fiat', 'stock']);
    const typeMatcher = get(matchers).find(matcher => matcher.key === 'type');
    assert(typeMatcher && 'string' in typeMatcher);
    expect(typeMatcher.suggestions()).toEqual(['fiat', 'stock']);
  });

  it('should validate the type against the provided suggestions', () => {
    const { matchers } = useCustomAssetFilter(['fiat', 'stock']);
    const typeMatcher = get(matchers).find(matcher => matcher.key === 'type');
    assert(typeMatcher && 'string' in typeMatcher);
    expect(typeMatcher.validate('fiat')).toBe(true);
    expect(typeMatcher.validate('crypto')).toBe(false);
  });

  it('should react to changes in a reactive suggestions ref', () => {
    const suggestions = ref<string[]>(['fiat']);
    const { matchers } = useCustomAssetFilter(suggestions);
    set(suggestions, ['stock']);
    const typeMatcher = get(matchers).find(matcher => matcher.key === 'type');
    assert(typeMatcher && 'string' in typeMatcher);
    expect(typeMatcher.suggestions()).toEqual(['stock']);
  });

  it('should keep name and type route values as optional strings', () => {
    const { RouteFilterSchema } = useCustomAssetFilter([]);
    assert(RouteFilterSchema);
    expect(RouteFilterSchema.parse({ custom_asset_type: 'fiat', name: 'gold' })).toEqual({
      custom_asset_type: 'fiat',
      name: 'gold',
    });
    expect(RouteFilterSchema.parse({})).toEqual({});
  });
});
