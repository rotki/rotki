import type { StubInstance } from '@test/utils/component-vm';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { EvmTokenKind, type SupportedAsset } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { computed } from 'vue';
import { CUSTOM_ASSET, EVM_TOKEN, HYPERLIQUID_TOKEN, SOLANA_TOKEN } from '@/modules/assets/types';
import '@test/i18n';

const { fetchTokenDetails } = vi.hoisted(() => ({
  fetchTokenDetails: vi.fn<(payload: { address: string; evmChain: string }) => Promise<Record<string, unknown>>>(),
}));

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: vi.fn().mockReturnValue({
    fetchTokenDetails,
  }),
}));

vi.mock('@/modules/assets/api/use-asset-management-api', () => ({
  useAssetManagementApi: vi.fn().mockReturnValue({
    addAsset: vi.fn().mockResolvedValue({ identifier: 'new' }),
    editAsset: vi.fn().mockResolvedValue(true),
  }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn().mockReturnValue({
    allEvmChains: computed(() => [{ label: 'Ethereum', name: 'ethereum' }]),
    txEvmChains: computed(() => [{ evmChainName: 'ethereum' }]),
  }),
}));

const ManagedAssetForm = (await import('@/modules/assets/admin/managed/ManagedAssetForm.vue')).default;

const EVM_ADDRESS = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48';
const SOLANA_ADDRESS = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v';
const HYPERLIQUID_ADDRESS = '0x0d01dc56dcaaca66ad901c959b4011ec';

function inputStub(name: string): Record<string, unknown> {
  return {
    emits: ['update:modelValue', 'blur'],
    name,
    props: ['modelValue', 'errorMessages', 'disabled', 'options', 'label'],
    template: '<div />',
  };
}

describe('managedAssetForm', () => {
  let wrapper: VueWrapper<InstanceType<typeof ManagedAssetForm>>;

  const evmToken = (overrides: Partial<SupportedAsset> = {}): SupportedAsset => ({
    address: EVM_ADDRESS,
    assetType: EVM_TOKEN,
    decimals: 6,
    evmChain: 'ethereum',
    identifier: 'test-asset',
    isRebasing: false,
    name: 'USD Coin',
    symbol: 'USDC',
    tokenKind: EvmTokenKind.ERC20,
    ...overrides,
  });

  beforeEach(() => {
    fetchTokenDetails.mockReset();
    fetchTokenDetails.mockResolvedValue({});
    setActivePinia(createPinia());
    vi.useFakeTimers();
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.useRealTimers();
  });

  function createWrapper(
    modelValue: SupportedAsset = evmToken(),
    props: Record<string, unknown> = {},
  ): VueWrapper<InstanceType<typeof ManagedAssetForm>> {
    return mount(ManagedAssetForm, {
      global: {
        stubs: {
          AssetIconForm: true,
          AssetSelect: inputStub('AssetSelect'),
          ChainDisplay: true,
          CopyButton: true,
          DateTimePicker: inputStub('DateTimePicker'),
          HelpLink: true,
          RuiMenuSelect: inputStub('RuiMenuSelect'),
          RuiSwitch: inputStub('RuiSwitch'),
          RuiTextField: inputStub('RuiTextField'),
          UnderlyingTokenManager: true,
        },
      },
      props: {
        assetTypes: [EVM_TOKEN, SOLANA_TOKEN, HYPERLIQUID_TOKEN, CUSTOM_ASSET],
        errorMessages: {},
        modelValue,
        ...props,
      },
    });
  }

  function field(testId: string): VueWrapper<StubInstance> {
    const found = wrapper.findComponent<StubInstance>(`[data-testid=${testId}]`);
    return found.exists() ? found : wrapper.find(`[data-testid=${testId}]`).findComponent<StubInstance>('*');
  }

  function messages(testId: string): string[] {
    const value: unknown = field(testId).props('errorMessages');
    assert(Array.isArray(value));
    return value.map(String);
  }

  it('should pass validation for a filled evm token', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(true);
  });

  it.each([
    [SOLANA_TOKEN, SOLANA_ADDRESS],
    [HYPERLIQUID_TOKEN, HYPERLIQUID_ADDRESS],
  ])('should pass validation for a filled %s', async (assetType, address) => {
    wrapper = createWrapper(evmToken({ address, assetType }));
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(true);
  });

  it('should fail validation with no asset type', async () => {
    wrapper = createWrapper(evmToken({ assetType: '' }));
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(false);
  });

  it('should require an address from a token that has one', async () => {
    wrapper = createWrapper(evmToken({ address: '' }));
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(false);
  });

  it.each([
    [EVM_TOKEN, SOLANA_ADDRESS],
    [SOLANA_TOKEN, EVM_ADDRESS],
    [HYPERLIQUID_TOKEN, SOLANA_ADDRESS],
  ])('should reject an address that is not %s shaped', async (assetType, address) => {
    wrapper = createWrapper(evmToken({ address, assetType }));
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.vm.validate();
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('address-input')).toEqual(['asset_form.validation.valid_address']);
  });

  it('should require a collectible id from an nft', async () => {
    wrapper = createWrapper(evmToken({ collectibleId: '', tokenKind: EvmTokenKind.ERC721 }));
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(false);
  });

  it('should not ask a fungible token for a collectible id', async () => {
    wrapper = createWrapper(evmToken({ collectibleId: '' }));
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(true);
  });

  it.each([
    ['coingecko'],
    ['cryptocompare'],
    ['protocol'],
    ['symbol'],
    ['name'],
  ] as const)('should not require %s', async (key) => {
    wrapper = createWrapper(evmToken({ [key]: '' }));
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(true);
  });

  it('should show no message before anything is edited', async () => {
    wrapper = createWrapper(evmToken({ address: '' }));
    await vi.advanceTimersToNextTimerAsync();

    expect(field('address-input').exists()).toBe(true);
    expect(messages('address-input')).toEqual([]);
    expect(messages('type-select')).toEqual([]);
  });

  it('should report a missing address once, in this app words', async () => {
    wrapper = createWrapper(evmToken({ address: '' }));
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.vm.validate();
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('address-input')).toEqual(['asset_form.validation.address_non_empty']);
  });

  it('should report a missing asset type in this app words', async () => {
    wrapper = createWrapper(evmToken({ assetType: '' }));
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.vm.validate();
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('type-select')).toEqual(['asset_form.validation.asset_type_non_empty']);
  });

  it('should show a server error on an untouched field', async () => {
    const errorMessages: ValidationErrors = { symbol: ['already taken'] };
    wrapper = createWrapper(evmToken(), { errorMessages });
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('symbol-input')).toEqual(['already taken']);
  });

  describe('writing back to the model', () => {
    function lastModel(): SupportedAsset {
      const emitted = wrapper.emitted<[SupportedAsset]>('update:modelValue');
      const last = emitted?.at(-1);
      assert(last);
      return last[0];
    }

    async function openOptional(): Promise<void> {
      await wrapper.find('[data-accordion-trigger]').trigger('click');
      await vi.advanceTimersToNextTimerAsync();
    }

    function labelled(name: string, label: string): VueWrapper<StubInstance> {
      const found = wrapper
        .findAllComponents<StubInstance>({ name })
        .find(component => component.props('label') === label);
      assert(found);
      return found;
    }

    it('should carry a picked swapped-for asset into the model', async () => {
      wrapper = createWrapper();
      await vi.advanceTimersToNextTimerAsync();

      await openOptional();

      labelled('AssetSelect', 'asset_form.labels.swapped_for').vm.$emit('update:modelValue', 'ETH');
      await vi.advanceTimersToNextTimerAsync();

      expect(lastModel().swappedFor).toBe('ETH');
    });

    it('should carry a picked forked asset into the model', async () => {
      wrapper = createWrapper(evmToken({ address: '', assetType: CUSTOM_ASSET }));
      await vi.advanceTimersToNextTimerAsync();

      await openOptional();

      labelled('AssetSelect', 'asset_form.labels.forked').vm.$emit('update:modelValue', 'BTC');
      await vi.advanceTimersToNextTimerAsync();

      expect(lastModel().forked).toBe('BTC');
    });

    it('should carry the rebasing switch into the model', async () => {
      wrapper = createWrapper();
      await vi.advanceTimersToNextTimerAsync();

      await openOptional();

      const rebasing = wrapper.findComponent<StubInstance>({ name: 'RuiSwitch' });
      assert(rebasing.exists());
      rebasing.vm.$emit('update:modelValue', true);
      await vi.advanceTimersToNextTimerAsync();

      expect(lastModel().isRebasing).toBe(true);
    });

    it('should carry a picked start date into the model', async () => {
      wrapper = createWrapper();
      await vi.advanceTimersToNextTimerAsync();

      await openOptional();

      const started = labelled('DateTimePicker', 'asset_form.labels.started');
      expect(started.props('modelValue')).toBe(0);
      started.vm.$emit('update:modelValue', 1_600_000_000);
      await vi.advanceTimersToNextTimerAsync();

      expect(lastModel().started).toBe(1_600_000_000);
    });

    it('should turn the typed decimals into a number', async () => {
      wrapper = createWrapper();
      await vi.advanceTimersToNextTimerAsync();

      expect(field('decimal-input').props('modelValue')).toBe('6');
      field('decimal-input').vm.$emit('update:modelValue', '18');
      await vi.advanceTimersToNextTimerAsync();

      expect(lastModel().decimals).toBe(18);
    });

    it('should carry a typed name into the model', async () => {
      wrapper = createWrapper();
      await vi.advanceTimersToNextTimerAsync();

      field('name-input').vm.$emit('update:modelValue', 'Circle USD');
      await vi.advanceTimersToNextTimerAsync();

      expect(lastModel().name).toBe('Circle USD');
    });

    it('should not report an edit the form never made', async () => {
      wrapper = createWrapper();
      await vi.advanceTimersToNextTimerAsync();

      expect(wrapper.emitted('update:modelValue')).toBeUndefined();
      expect(wrapper.emitted('update:stateUpdated')).toBeUndefined();
    });

    it('should keep a cleared optional field empty rather than absent', async () => {
      wrapper = createWrapper();
      await vi.advanceTimersToNextTimerAsync();

      field('symbol-input').vm.$emit('update:modelValue', '');
      await vi.advanceTimersToNextTimerAsync();

      expect(lastModel().symbol).toBe('');
    });

    it('should flag the dialog once a field is edited', async () => {
      wrapper = createWrapper();
      await vi.advanceTimersToNextTimerAsync();

      field('symbol-input').vm.$emit('update:modelValue', 'USDC2');
      await vi.advanceTimersToNextTimerAsync();

      expect(wrapper.emitted<[boolean]>('update:stateUpdated')?.at(-1)).toEqual([true]);
    });

    it('should re-derive which fields apply from the edited type', async () => {
      wrapper = createWrapper();
      await vi.advanceTimersToNextTimerAsync();

      expect(field('chain-select').exists()).toBe(true);

      field('type-select').vm.$emit('update:modelValue', CUSTOM_ASSET);
      await vi.advanceTimersToNextTimerAsync();

      expect(lastModel().assetType).toBe(CUSTOM_ASSET);
      expect(wrapper.find('[data-testid=chain-select]').exists()).toBe(false);
    });
  });

  it('should clear the server errors when the asset type changes', async () => {
    const errorMessages: ValidationErrors = { symbol: ['already taken'] };
    wrapper = createWrapper(evmToken(), { errorMessages });
    await vi.advanceTimersToNextTimerAsync();

    field('type-select').vm.$emit('update:modelValue', SOLANA_TOKEN);
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.emitted<[ValidationErrors]>('update:errorMessages')?.at(-1)).toEqual([{}]);
  });

  describe('token lookup', () => {
    const OTHER_ADDRESS = '0x6B175474E89094C44Da98b954EedeAC495271d0F';

    it('should look a token up when its address is set while adding', async () => {
      wrapper = createWrapper(evmToken({ address: '' }));
      await vi.advanceTimersToNextTimerAsync();

      field('address-input').vm.$emit('update:modelValue', OTHER_ADDRESS);
      await vi.advanceTimersToNextTimerAsync();

      expect(fetchTokenDetails).toHaveBeenCalledWith({ address: OTHER_ADDRESS, evmChain: 'ethereum' });
    });

    it('should not look the token up when the address is set while editing', async () => {
      wrapper = createWrapper(evmToken(), { editMode: true });
      await vi.advanceTimersToNextTimerAsync();

      field('address-input').vm.$emit('update:modelValue', OTHER_ADDRESS);
      await vi.advanceTimersToNextTimerAsync();

      expect(lastAddress()).toBe(OTHER_ADDRESS);
      expect(fetchTokenDetails).not.toHaveBeenCalled();
    });

    function lastAddress(): string | null | undefined {
      const last = wrapper.emitted<[SupportedAsset]>('update:modelValue')?.at(-1);
      assert(last);
      return last[0].address;
    }
  });
});
