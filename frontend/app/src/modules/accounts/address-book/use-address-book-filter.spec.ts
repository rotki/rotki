import { assert, describe, expect, it, vi } from 'vitest';
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

  // The fields are declared in `address-book-fields.ts` and covered by its own spec. What is left
  // here is the URL round-trip, which is the only thing this schema still owns.
  it('should keep the name value as a single string', () => {
    const { RouteFilterSchema } = useAddressBookFilter();
    assert(RouteFilterSchema);
    expect(RouteFilterSchema.parse({ nameSubstring: 'alice' })).toEqual({ nameSubstring: 'alice' });
  });

  it('should coerce a single address into an array', () => {
    const { RouteFilterSchema } = useAddressBookFilter();
    assert(RouteFilterSchema);
    expect(RouteFilterSchema.parse({ address: '0xabc' })).toEqual({ address: ['0xabc'] });
  });

  it('should keep multiple addresses as an array', () => {
    const { RouteFilterSchema } = useAddressBookFilter();
    assert(RouteFilterSchema);
    expect(RouteFilterSchema.parse({ address: ['0xabc', '0xdef'] })).toEqual({ address: ['0xabc', '0xdef'] });
  });

  it('should allow an empty route filter', () => {
    const { RouteFilterSchema } = useAddressBookFilter();
    assert(RouteFilterSchema);
    expect(RouteFilterSchema.parse({})).toEqual({});
  });
});
