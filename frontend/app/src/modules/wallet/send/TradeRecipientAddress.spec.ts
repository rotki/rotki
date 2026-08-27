import type { RecipientOption } from '@/modules/wallet/send/use-trade-recipient-address';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, nextTick } from 'vue';
import TradeRecipientAddress from '@/modules/wallet/send/TradeRecipientAddress.vue';

const ALICE = '0x9531C059098e3d194fF87FebB587aB07B30B1306';

const recipientApi = {
  applySearchInput: vi.fn(),
  directOptions: ref<RecipientOption[]>([]),
  filteredAddressBookOptions: ref<string[]>([]),
  handleFocusChange: vi.fn(),
  modelAddressBookSearch: ref<string>(''),
  modelOpenOptionsDialog: ref<boolean>(false),
  modelOpenSuggestionsMenu: ref<boolean>(false),
  modelSearchValue: ref<string>(''),
  reset: vi.fn(),
  resolvingEns: ref<boolean>(false),
  searchAddresses: vi.fn(),
  select: vi.fn(),
  trackedAddresses: ref<string[]>([]),
  valid: ref<boolean>(true),
};

vi.mock('@/modules/wallet/send/use-trade-recipient-address', () => ({
  useTradeRecipientAddress: (): typeof recipientApi => recipientApi,
}));

const connected = ref<boolean>(false);

vi.mock('@/modules/wallet/use-wallet-store', () => ({
  useWalletStore: (): { connected: typeof connected } => ({ connected }),
}));

const RuiMenuStub = defineComponent({
  name: 'RuiMenu',
  props: { modelValue: { default: false, type: Boolean } },
  emits: ['update:modelValue'],
  template: '<div><slot name="activator" :attrs="{}" /><slot :width="300" /></div>',
});

const RuiDialogStub = defineComponent({
  name: 'RuiDialog',
  props: { modelValue: { default: false, type: Boolean } },
  emits: ['update:modelValue'],
  template: '<div v-if="modelValue"><slot /></div>',
});

const addressDisplayStub = defineComponent({
  name: 'TradeAddressDisplay',
  props: {
    address: { default: '', type: String },
    chain: { default: '', type: String },
    name: { default: '', type: String },
  },
  template: '<div class="address-display">{{ address }}</div>',
});

async function createWrapper(props: { model?: string; showWarning?: boolean } = {}): Promise<VueWrapper<InstanceType<typeof TradeRecipientAddress>>> {
  const wrapper = mount(TradeRecipientAddress, {
    global: {
      stubs: {
        RuiDialog: RuiDialogStub,
        RuiMenu: RuiMenuStub,
        TradeAddressDisplay: addressDisplayStub,
      },
    },
    props: {
      chain: 'eth',
      modelValue: props.model ?? '',
      showWarning: props.showWarning ?? false,
    },
  });

  await nextTick();
  return wrapper;
}

describe('tradeRecipientAddress', () => {
  let wrapper: VueWrapper<InstanceType<typeof TradeRecipientAddress>>;

  beforeEach(() => {
    vi.clearAllMocks();
    set(connected, false);
    set(recipientApi.valid, true);
    set(recipientApi.directOptions, []);
    set(recipientApi.trackedAddresses, []);
    set(recipientApi.filteredAddressBookOptions, []);
    set(recipientApi.modelOpenOptionsDialog, false);
    set(recipientApi.modelSearchValue, '');
    set(recipientApi.resolvingEns, false);
  });

  afterEach(() => {
    wrapper.unmount();
  });

  describe('without a recipient', () => {
    beforeEach(async () => {
      wrapper = await createWrapper();
    });

    it('should search as the user types and take what was typed on blur', async () => {
      const input = wrapper.find('[data-testid=recipient-search]');
      await input.setValue(ALICE);

      expect(get(recipientApi.modelSearchValue)).toBe(ALICE);

      await input.trigger('blur');

      expect(recipientApi.applySearchInput).toHaveBeenCalledOnce();
    });

    it('should offer what the search found and pick the one that is clicked', async () => {
      set(recipientApi.directOptions, [{ address: ALICE, name: 'alice.eth' }]);
      await nextTick();

      const option = wrapper.findAllComponents(addressDisplayStub)
        .find(candidate => candidate.props('address') === ALICE);
      expect(option?.props('name')).toBe('alice.eth');

      await option?.trigger('click');

      expect(recipientApi.select).toHaveBeenCalledWith(ALICE);
    });

    it('should say it is resolving instead of offering anything', async () => {
      set(recipientApi.directOptions, [{ address: ALICE }]);
      set(recipientApi.resolvingEns, true);
      await nextTick();

      expect(wrapper.text()).toContain('trade.recipient.resolving_ens');
      expect(wrapper.findAllComponents(addressDisplayStub)).toHaveLength(0);
    });

    it('should open the address book on request', async () => {
      await wrapper.find('[data-testid=recipient-open-address-book]').trigger('click');

      expect(get(recipientApi.modelOpenOptionsDialog)).toBe(true);
    });

    it('should say when the address book has nothing to offer', async () => {
      set(recipientApi.modelOpenOptionsDialog, true);
      await nextTick();

      expect(wrapper.text()).toContain('trade.recipient.no_addresses_found');
    });

    it('should mark the field when what is in it is not an address', async () => {
      expect(wrapper.text()).toContain('trade.to_address.label');
      expect(wrapper.find('[data-testid=recipient-field]').classes()).not.toContain('!border-rui-error');

      await wrapper.setProps({ modelValue: 'not-an-address' });
      set(recipientApi.valid, false);
      await nextTick();

      expect(wrapper.find('[data-testid=recipient-field]').classes()).toContain('!border-rui-error');
    });
  });

  describe('with a recipient', () => {
    beforeEach(async () => {
      wrapper = await createWrapper({ model: ALICE });
    });

    it('should show the recipient instead of the search input', () => {
      expect(wrapper.find('[data-testid=recipient-search]').exists()).toBe(false);
      expect(wrapper.findComponent(addressDisplayStub).props('address')).toBe(ALICE);
    });

    it('should clear the recipient on request', async () => {
      await wrapper.find('[data-testid=recipient-clear]').trigger('click');

      expect(recipientApi.reset).toHaveBeenCalledOnce();
    });

    it('should warn about an address the wallet never interacted with, only while connected', async () => {
      await wrapper.setProps({ showWarning: true });
      expect(wrapper.text()).not.toContain('trade.never_interacted');

      set(connected, true);
      await nextTick();

      expect(wrapper.text()).toContain('trade.never_interacted');

      await wrapper.setProps({ showWarning: false });
      expect(wrapper.text()).not.toContain('trade.never_interacted');
    });
  });
});
