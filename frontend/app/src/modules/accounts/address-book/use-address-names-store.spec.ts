import { beforeEach, describe, expect, it } from 'vitest';
import { useAddressNamesStore } from '@/modules/accounts/address-book/use-address-names-store';

describe('useAddressNamesStore', () => {
  let store: ReturnType<typeof useAddressNamesStore>;
  setActivePinia(createPinia());

  beforeEach(() => {
    store = useAddressNamesStore();
    const { ensNames } = storeToRefs(store);
    set(ensNames, {});
  });

  describe('setEnsNames', () => {
    it('should set ens names', () => {
      store.setEnsNames({ '0xAddress1': 'name1.eth' });

      const { ensNames } = storeToRefs(store);
      expect(get(ensNames)).toStrictEqual({ '0xAddress1': 'name1.eth' });
    });

    it('should merge with existing ens names', () => {
      store.setEnsNames({ '0xAddress1': 'name1.eth' });
      store.setEnsNames({ '0xAddress2': 'name2.eth' });

      const { ensNames } = storeToRefs(store);
      expect(get(ensNames)).toStrictEqual({
        '0xAddress1': 'name1.eth',
        '0xAddress2': 'name2.eth',
      });
    });

    it('should overwrite existing ens name for same address', () => {
      store.setEnsNames({ '0xAddress1': 'old.eth' });
      store.setEnsNames({ '0xAddress1': 'new.eth' });

      const { ensNames } = storeToRefs(store);
      expect(get(ensNames)).toStrictEqual({ '0xAddress1': 'new.eth' });
    });
  });
});
