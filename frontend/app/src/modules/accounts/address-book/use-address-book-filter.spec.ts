import { describe, expect, it, vi } from 'vitest';
import { useAddressBookFilter } from '@/modules/accounts/address-book/use-address-book-filter';

vi.mock('vue-i18n', async importOriginal => ({
  ...await importOriginal<typeof import('vue-i18n')>(),
  useI18n: (): { t: (key: string) => string } => ({ t: (key: string): string => key }),
}));

describe('useAddressBookFilter', () => {
  it('should start with an empty filter', () => {
    const { filters } = useAddressBookFilter();
    expect(get(filters)).toEqual({});
  });

  // The URL round-trip is asserted in `address-book-fields.spec.ts`: the url shape is derived from
  // the fields, so it is proved against the field list rather than against a second declaration.
});
