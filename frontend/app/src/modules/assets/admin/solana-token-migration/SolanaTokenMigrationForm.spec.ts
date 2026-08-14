import type { ComponentPublicInstance } from 'vue';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import '@test/i18n';

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: vi.fn().mockReturnValue({
    getAssetInfo: vi.fn().mockReturnValue({ name: 'Old token', symbol: 'OLD' }),
  }),
}));

const SolanaTokenMigrationForm = (
  await import('@/modules/assets/admin/solana-token-migration/SolanaTokenMigrationForm.vue')
).default;

/** Real mint addresses, since the address rule runs the base58 check on them. */
const VALID_ADDRESS = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v';
const OTHER_ADDRESS = 'So11111111111111111111111111111111111111112';

interface MigrationData {
  address: string;
  decimals: number | null;
  tokenKind: string;
}

/** The stubs below declare their props at runtime, so their instances are typed loosely. */
type StubInstance = ComponentPublicInstance<Record<string, unknown>>;

function inputStub(name: string): Record<string, unknown> {
  return {
    emits: ['update:modelValue', 'blur', 'input'],
    name,
    props: ['modelValue', 'errorMessages', 'disabled', 'options'],
    template: '<div />',
  };
}

describe('solanaTokenMigrationForm', () => {
  let wrapper: VueWrapper<InstanceType<typeof SolanaTokenMigrationForm>>;

  const baseModel = (): MigrationData => ({
    address: VALID_ADDRESS,
    decimals: 6,
    tokenKind: 'spl-token',
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
    modelValue: MigrationData = baseModel(),
    props: Record<string, unknown> = {},
  ): VueWrapper<InstanceType<typeof SolanaTokenMigrationForm>> {
    return mount(SolanaTokenMigrationForm, {
      global: {
        stubs: {
          AmountInput: inputStub('AmountInput'),
          RuiMenuSelect: inputStub('RuiMenuSelect'),
          RuiTextField: inputStub('RuiTextField'),
        },
      },
      props: { errorMessages: {}, modelValue, ...props },
    });
  }

  /** The test ids sit on the wrapping cell, which is what the e2e page object addresses too. */
  function field(testId: string): VueWrapper<StubInstance> {
    return wrapper.find(`[data-testid=${testId}]`).findComponent<StubInstance>('*');
  }

  function messages(testId: string): string[] {
    const value: unknown = field(testId).props('errorMessages');
    assert(Array.isArray(value));
    return value.map(String);
  }

  async function edit(testId: string, value: string): Promise<void> {
    const input = field(testId);
    input.vm.$emit('update:modelValue', value);
    input.vm.$emit('input', value);
    input.vm.$emit('blur');
    await vi.advanceTimersToNextTimerAsync();
  }

  function lastModel(): MigrationData {
    const updates = wrapper.emitted<[MigrationData]>('update:modelValue');
    assert(updates);
    return updates.at(-1)![0];
  }

  it('should pass validation for a real address with a kind and decimals', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(true);
  });

  it('should accept zero decimals', async () => {
    wrapper = createWrapper({ ...baseModel(), decimals: 0 });
    await vi.advanceTimersToNextTimerAsync();

    // Zero is a value like any other here, which is what vuelidate's required reported too.
    expect(await wrapper.vm.validate()).toBe(true);
  });

  it.each([
    ['address', ''],
    ['tokenKind', ''],
    ['decimals', null],
  ] as const)('should fail validation when %s is missing', async (key, empty) => {
    wrapper = createWrapper({ ...baseModel(), [key]: empty });
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(false);
  });

  it('should reject an address that is not base58', async () => {
    wrapper = createWrapper({ ...baseModel(), address: 'not-a-solana-address' });
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(false);
  });

  it('should show no message before anything is edited', async () => {
    wrapper = createWrapper({ address: '', decimals: null, tokenKind: '' });
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('address-input')).toEqual([]);
    expect(messages('decimals-input')).toEqual([]);
    expect(messages('token-kind-select')).toEqual([]);
  });

  it('should report a missing value in vuelidate english', async () => {
    wrapper = createWrapper({ address: '', decimals: null, tokenKind: '' });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.vm.validate();
    await vi.advanceTimersToNextTimerAsync();

    // None of the three rules was given a message, so all three fall back to the library's own
    // untranslated string.
    expect(messages('address-input')).toEqual(['Value is required']);
    expect(messages('decimals-input')).toEqual(['Value is required']);
    expect(messages('token-kind-select')).toEqual(['Value is required']);
  });

  it('should say nothing at all about a malformed address', async () => {
    wrapper = createWrapper({ ...baseModel(), address: 'not-a-solana-address' });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.vm.validate();
    await vi.advanceTimersToNextTimerAsync();

    // The base58 rule is a bare function, and vuelidate defaults a bare rule's message to the empty
    // string, so the field goes red with nothing written under it.
    expect(messages('address-input')).toEqual(['']);
  });

  it('should parse the typed decimals into a number', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await edit('decimals-input', '18');

    expect(lastModel().decimals).toBe(18);
  });

  it.each([
    ['', null],
    ['abc', null],
  ])('should store %s decimals as null', async (typed, expected) => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await edit('decimals-input', typed);

    expect(lastModel().decimals).toBe(expected);
  });

  it('should write an edited address back into the model', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await edit('address-input', OTHER_ADDRESS);

    expect(lastModel().address).toBe(OTHER_ADDRESS);
  });

  it('should drop a server error for the field being typed into', async () => {
    const errorMessages: ValidationErrors = {
      address: ['already migrated'],
      decimals: ['wrong'],
    };
    wrapper = createWrapper(baseModel(), { errorMessages });
    await vi.advanceTimersToNextTimerAsync();

    await edit('address-input', OTHER_ADDRESS);

    const updates = wrapper.emitted<[ValidationErrors]>('update:errorMessages');
    assert(updates);
    expect(updates.at(-1)![0]).toEqual({ decimals: ['wrong'] });
  });

  it('should flag stateUpdated once a field is edited', async () => {
    wrapper = createWrapper();
    // Settle the mounted work first, so what follows is the only edit in play.
    await vi.advanceTimersByTimeAsync(600);

    await edit('address-input', OTHER_ADDRESS);

    expect(wrapper.emitted('update:stateUpdated')?.at(-1)).toEqual([true]);
  });

  it('should lock every field while the migration runs', async () => {
    wrapper = createWrapper(baseModel(), { loading: true });
    await vi.advanceTimersToNextTimerAsync();

    expect(field('address-input').props('disabled')).toBe(true);
    expect(field('decimals-input').props('disabled')).toBe(true);
    expect(field('token-kind-select').props('disabled')).toBe(true);
  });
});
