import type { ComponentPublicInstance } from 'vue';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { EvmTokenKind, type SupportedAsset } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { CUSTOM_ASSET, EVM_TOKEN, HYPERLIQUID_TOKEN, SOLANA_TOKEN } from '@/modules/assets/types';
import '@test/i18n';

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: vi.fn().mockReturnValue({
    fetchTokenDetails: vi.fn().mockResolvedValue({}),
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

/** Real addresses, since the address rules run format checks on them. */
const EVM_ADDRESS = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48';
const SOLANA_ADDRESS = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v';
const HYPERLIQUID_ADDRESS = '0x0d01dc56dcaaca66ad901c959b4011ec';

/** The stubs below declare their props at runtime, so their instances are typed loosely. */
type StubInstance = ComponentPublicInstance<Record<string, unknown>>;

function inputStub(name: string): Record<string, unknown> {
  return {
    emits: ['update:modelValue', 'blur'],
    name,
    props: ['modelValue', 'errorMessages', 'disabled', 'options'],
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

  /** Some test ids sit on the field, some on the cell around it. */
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

    // These carry a rule that always returns true. It is where server errors land, not a rule.
    expect(await wrapper.vm.validate()).toBe(true);
  });

  it('should show no message before anything is edited', async () => {
    // The address fields only exist once a type is chosen, so the type stays set here.
    wrapper = createWrapper(evmToken({ address: '' }));
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('address-input')).toEqual([]);
    expect(messages('type-select')).toEqual([]);
  });

  // Before the swap this reported two of vuelidate's own untranslated strings: the empty field was
  // called missing and malformed at once.
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

  // Deliberately flipped in the zod swap. Vuelidate read external results through $errors, so a
  // rejected save said nothing at all on a field the user had not been in.
  it('should show a server error on an untouched field', async () => {
    const errorMessages: ValidationErrors = { symbol: ['already taken'] };
    wrapper = createWrapper(evmToken(), { errorMessages });
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('symbol-input')).toEqual(['already taken']);
  });

  // The form edits its own state and the dialog saves what it reads off the model, so an edit that
  // never reaches the model is an edit that never gets persisted. Before the fields bound to
  // `form.state` this direction was the one thing nothing here covered.
  describe('writing back to the model', () => {
    function lastModel(): SupportedAsset {
      const emitted = wrapper.emitted<[SupportedAsset]>('update:modelValue');
      const last = emitted?.at(-1);
      assert(last);
      return last[0];
    }

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

      // The negative control for the test above: opening the form is not an edit, so a passing
      // assertion there cannot be the model simply echoing what it was seeded with.
      expect(wrapper.emitted('update:modelValue')).toBeUndefined();
      expect(wrapper.emitted('update:stateUpdated')).toBeUndefined();
    });

    it('should keep a cleared optional field empty rather than absent', async () => {
      wrapper = createWrapper();
      await vi.advanceTimersToNextTimerAsync();

      // The state holds '' rather than clearing the key, and `buildManagedAssetPayload` is what
      // turns it back into an absent field. Clearing it here must not produce null.
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

      // The chain select belongs to an evm token alone, and the rules that ask for an address read
      // the same answer, so this is what proves the kind follows the state the fields write into.
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

    // The messages differ per asset type, so what the server said about the last one cannot stand.
    field('type-select').vm.$emit('update:modelValue', SOLANA_TOKEN);
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.emitted<[ValidationErrors]>('update:errorMessages')?.at(-1)).toEqual([{}]);
  });
});
