import { describe, expect, it, vi } from 'vitest';
import { useCustomAssetFilter } from '@/modules/assets/admin/custom/use-custom-assets-filter';

vi.mock('vue-i18n', async importOriginal => ({
  ...await importOriginal<typeof import('vue-i18n')>(),
  useI18n: (): { t: (key: string) => string } => ({ t: (key: string): string => key }),
}));

describe('useCustomAssetFilter', () => {
  it('should start with an empty filter', () => {
    const { filters } = useCustomAssetFilter();
    expect(get(filters)).toEqual({});
  });

  // The fields are declared in `custom-asset-fields.ts`, with their suggestions and validation, and
  // covered by its own spec, which is also where the URL round-trip is now asserted: the url shape
  // is derived from those fields.
});
