import { Blockchain } from '@rotki/common/lib/blockchain';
import type { BtcAccountData } from '@/types/blockchain/accounts';

vi.mock('@/composables/api/blockchain/accounts', () => ({
  useBlockchainAccountsApi: vi.fn().mockReturnValue({
    deleteXpub: vi.fn().mockResolvedValue(1),
  }),
}));

function standalone(id: number, tags: string[]) {
  return {
    address: `address-${id}`,
    label: '',
    tags,
  };
}

describe('store::blockchain/accounts/btc', () => {
  setActivePinia(createPinia());
  let store: ReturnType<typeof useBtcAccountsStore>;

  beforeEach(() => {
    store = useBtcAccountsStore();
    vi.clearAllMocks();
  });

  const tag = 'tag_1';

  it('update', () => {
    const { btc } = storeToRefs(store);

    const data = {
      standalone: [standalone(1, [tag])],
      xpubs: [
        {
          xpub: 'xpub-1',
          derivationPath: null,
          label: '',
          tags: ['tag_2'],
          addresses: [standalone(2, []), standalone(3, [])],
        },
      ],
    };

    store.update(Blockchain.BTC, data);

    expect(get(btc)).toEqual(data);
  });

  it('removeTag', () => {
    const { btc } = storeToRefs(store);

    const removedTags: BtcAccountData = {
      standalone: [standalone(1, [])],
      xpubs: [
        {
          xpub: 'xpub-1',
          derivationPath: null,
          label: '',
          tags: ['tag_2'],
          addresses: [standalone(2, []), standalone(3, [])],
        },
      ],
    };
    store.removeTag(tag);

    expect(get(btc)).toEqual(removedTags);
  });
});
