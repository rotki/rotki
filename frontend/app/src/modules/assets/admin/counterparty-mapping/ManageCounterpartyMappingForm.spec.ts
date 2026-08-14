import type { ComponentPublicInstance } from 'vue';
import type { CounterpartyMapping } from '@/modules/assets/admin/counterparty-mapping/schema';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import ManageCounterpartyMappingForm from '@/modules/assets/admin/counterparty-mapping/ManageCounterpartyMappingForm.vue';
import '@test/i18n';

/** The stubs below declare their props at runtime, so their instances are typed loosely. */
type StubInstance = ComponentPublicInstance<Record<string, unknown>>;

/** Every field is a third-party input, so they are stubbed down to what the form reads back. */
function inputStub(name: string): Record<string, unknown> {
  return {
    emits: ['update:modelValue'],
    name,
    props: ['modelValue', 'errorMessages', 'disabled'],
    template: '<div />',
  };
}

describe('manageCounterpartyMappingForm', () => {
  let wrapper: VueWrapper<InstanceType<typeof ManageCounterpartyMappingForm>>;

  const baseModel = (): CounterpartyMapping => ({
    asset: 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
    counterparty: 'uniswap-v2',
    counterpartySymbol: 'USDC',
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
    modelValue: CounterpartyMapping = baseModel(),
    props: Record<string, unknown> = {},
  ): VueWrapper<InstanceType<typeof ManageCounterpartyMappingForm>> {
    return mount(ManageCounterpartyMappingForm, {
      global: {
        stubs: {
          AssetSelect: inputStub('AssetSelect'),
          CounterpartyInput: inputStub('CounterpartyInput'),
          RuiTextField: inputStub('RuiTextField'),
        },
      },
      props: { errorMessages: {}, modelValue, ...props },
    });
  }

  function field(testId: string): VueWrapper<StubInstance> {
    return wrapper.findComponent<StubInstance>(`[data-testid=${testId}]`);
  }

  function messages(testId: string): string[] {
    const value: unknown = field(testId).props('errorMessages');
    assert(Array.isArray(value));
    return value.map(String);
  }

  async function edit(testId: string, value: string | undefined): Promise<void> {
    field(testId).vm.$emit('update:modelValue', value);
    await vi.advanceTimersToNextTimerAsync();
  }

  function lastModel(): CounterpartyMapping {
    const updates = wrapper.emitted<[CounterpartyMapping]>('update:modelValue');
    assert(updates);
    return updates.at(-1)![0];
  }

  it('should pass validation when every field is filled', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(true);
  });

  it.each([
    ['asset'],
    ['counterparty'],
    ['counterpartySymbol'],
  ] as const)('should fail validation when %s is empty', async (key) => {
    const model = baseModel();
    model[key] = '';
    wrapper = createWrapper(model);
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(false);
  });

  it('should treat a whitespace-only symbol as empty', async () => {
    wrapper = createWrapper({ ...baseModel(), counterpartySymbol: '   ' });
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(false);
  });

  it('should show no message before anything is edited', async () => {
    wrapper = createWrapper({ asset: '', counterparty: '', counterpartySymbol: '' });
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('counterparty')).toEqual([]);
    expect(messages('counterparty-symbol')).toEqual([]);
    expect(messages('counterparty-asset')).toEqual([]);
  });

  it('should reveal every message once validate runs', async () => {
    wrapper = createWrapper({ asset: '', counterparty: '', counterpartySymbol: '' });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.vm.validate();
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('counterparty')).toEqual([
      'asset_management.counterparty_mapping.form.counterparty_non_empty',
    ]);
    expect(messages('counterparty-symbol')).toEqual([
      'asset_management.counterparty_mapping.form.counterparty_symbol_non_empty',
    ]);
    expect(messages('counterparty-asset')).toEqual([
      'asset_management.cex_mapping.form.asset_non_empty',
    ]);
  });

  it('should show the symbol message once the field is emptied', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await edit('counterparty-symbol', '');

    expect(messages('counterparty-symbol')).toEqual([
      'asset_management.counterparty_mapping.form.counterparty_symbol_non_empty',
    ]);
    // The untouched fields stay quiet.
    expect(messages('counterparty')).toEqual([]);
  });

  it('should write an edit back into the model', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await edit('counterparty-symbol', 'DAI');

    expect(lastModel().counterpartySymbol).toBe('DAI');
    expect(lastModel().counterparty).toBe('uniswap-v2');
  });

  it('should write a cleared counterparty back as null', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    // The input is wrapped in nullDefined, so clearing it does not leave the field a string. The
    // payload type says otherwise, and the api is what the null reaches.
    await edit('counterparty', undefined);

    expect(lastModel().counterparty).toBeNull();
    expect(await wrapper.vm.validate()).toBe(false);
  });

  it('should flag stateUpdated once a field is edited', async () => {
    wrapper = createWrapper();
    // Settle the mounted work first, so what follows is the only edit in play.
    await vi.advanceTimersByTimeAsync(600);

    await edit('counterparty-symbol', 'DAI');

    expect(wrapper.emitted('update:stateUpdated')?.at(-1)).toEqual([true]);
  });

  it('should not flag stateUpdated before anything is edited', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersByTimeAsync(600);

    expect(wrapper.emitted('update:stateUpdated')?.at(-1)).not.toEqual([true]);
  });

  it('should lock the counterparty and its symbol while editing', async () => {
    wrapper = createWrapper(baseModel(), { editMode: true });
    await vi.advanceTimersToNextTimerAsync();

    expect(field('counterparty').props('disabled')).toBe(true);
    expect(field('counterparty-symbol').props('disabled')).toBe(true);
    // Repointing the mapping at another asset is the whole point of the edit dialog.
    expect(field('counterparty-asset').props('disabled')).toBeFalsy();
  });

  it('should keep a server error hidden until its field is touched', async () => {
    const errorMessages: ValidationErrors = { counterpartySymbol: ['already mapped'] };
    wrapper = createWrapper(baseModel(), { errorMessages });
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('counterparty-symbol')).toEqual([]);
  });
});
