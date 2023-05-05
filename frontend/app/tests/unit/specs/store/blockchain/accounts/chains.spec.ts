import { Blockchain } from '@rotki/common/lib/blockchain';
import { type GeneralAccountData } from '@/types/blockchain/accounts';

describe('store::blockchain/accounts/chains', () => {
  setActivePinia(createPinia());
  let store: ReturnType<typeof useChainsAccountsStore>;

  beforeEach(() => {
    store = useChainsAccountsStore();
    vi.clearAllMocks();
  });

  const address = '0x443E1f9b1c866E54e914822B7d3d7165EdB6e9Ea';
  const tag = 'tag_1';

  test('update', () => {
    const { optimism } = storeToRefs(store);
    const accounts: GeneralAccountData[] = [
      {
        address,
        label: 'test optimism',
        tags: [tag]
      }
    ];

    store.update(Blockchain.OPTIMISM, accounts);

    expect(get(optimism)).toEqual(accounts);
  });

  test('removeTag', () => {
    const { optimism, optimismAddresses } = storeToRefs(store);
    const newData: GeneralAccountData = {
      address,
      label: 'test optimism',
      tags: []
    };

    store.removeTag(tag);

    expect(get(optimism)).toEqual([newData]);
    expect(get(optimismAddresses)).toEqual([address]);
  });
});
