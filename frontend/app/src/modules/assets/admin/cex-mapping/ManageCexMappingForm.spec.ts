import type { ComponentPublicInstance } from 'vue';
import type { CexMapping } from '@/modules/assets/types';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import ManageCexMappingForm from '@/modules/assets/admin/cex-mapping/ManageCexMappingForm.vue';
import '@test/i18n';

/** The stubs below declare their props at runtime, so their instances are typed loosely. */
type StubInstance = ComponentPublicInstance<Record<string, unknown>>;

function inputStub(name: string): Record<string, unknown> {
  return {
    emits: ['update:modelValue'],
    name,
    props: ['modelValue', 'errorMessages', 'disabled', 'excludes'],
    template: '<div />',
  };
}

describe('manageCexMappingForm', () => {
  let wrapper: VueWrapper<InstanceType<typeof ManageCexMappingForm>>;

  const baseModel = (): CexMapping => ({
    asset: 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
    location: 'kraken',
    locationSymbol: 'USDC',
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
    modelValue: CexMapping = baseModel(),
    props: Record<string, unknown> = {},
  ): VueWrapper<InstanceType<typeof ManageCexMappingForm>> {
    return mount(ManageCexMappingForm, {
      global: {
        stubs: {
          AssetSelect: inputStub('AssetSelect'),
          ExchangeInput: inputStub('ExchangeInput'),
          LocationDisplay: { name: 'LocationDisplay', props: ['identifier'], template: '<div />' },
          RuiSwitch: inputStub('RuiSwitch'),
          RuiTextField: inputStub('RuiTextField'),
        },
      },
      props: {
        errorMessages: {},
        forAllExchanges: !modelValue.location,
        modelValue,
        ...props,
      },
    });
  }

  function stub(name: string): VueWrapper<StubInstance> {
    return wrapper.findComponent<StubInstance>({ name });
  }

  function messages(name: string): string[] {
    const value: unknown = stub(name).props('errorMessages');
    assert(Array.isArray(value));
    return value.map(String);
  }

  async function edit(name: string, value: string | undefined): Promise<void> {
    stub(name).vm.$emit('update:modelValue', value);
    await vi.advanceTimersToNextTimerAsync();
  }

  function lastModel(): CexMapping {
    const updates = wrapper.emitted<[CexMapping]>('update:modelValue');
    assert(updates);
    return updates.at(-1)![0];
  }

  it('should pass validation for a mapping tied to one exchange', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(true);
  });

  it('should pass validation with no exchange when it covers all of them', async () => {
    wrapper = createWrapper({ ...baseModel(), location: null });
    await vi.advanceTimersToNextTimerAsync();

    // The location rule is the only conditional one in the form: it is required unless the mapping
    // is being saved for every exchange.
    expect(await wrapper.vm.validate()).toBe(true);
  });

  it('should fail validation once the exchange is cleared on a single-exchange mapping', async () => {
    // The switch cannot be forced out of step with the payload: the form reads it off the location
    // on mount. Clearing the field afterwards is what leaves the two disagreeing.
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await edit('ExchangeInput', undefined);

    expect(await wrapper.vm.validate()).toBe(false);
    expect(messages('ExchangeInput')).toEqual([
      'asset_management.cex_mapping.form.location_non_empty',
    ]);
  });

  it.each([
    ['asset'],
    ['locationSymbol'],
  ] as const)('should fail validation when %s is empty whatever the switch says', async (key) => {
    wrapper = createWrapper({ ...baseModel(), [key]: '' }, { forAllExchanges: true });
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(false);
  });

  it('should show no message before anything is edited', async () => {
    wrapper = createWrapper({ asset: '', location: null, locationSymbol: '' }, { forAllExchanges: false });
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('ExchangeInput')).toEqual([]);
    expect(messages('RuiTextField')).toEqual([]);
    expect(messages('AssetSelect')).toEqual([]);
  });

  it('should reveal every message once validate runs', async () => {
    wrapper = createWrapper({ asset: '', location: 'kraken', locationSymbol: '' });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.vm.validate();
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('RuiTextField')).toEqual([
      'asset_management.cex_mapping.form.location_symbol_non_empty',
    ]);
    expect(messages('AssetSelect')).toEqual([
      'asset_management.cex_mapping.form.asset_non_empty',
    ]);
  });

  it('should say nothing about the exchange once the mapping covers all of them', async () => {
    wrapper = createWrapper({ asset: '', location: null, locationSymbol: '' }, { forAllExchanges: true });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.vm.validate();
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('ExchangeInput')).toEqual([]);
    expect(messages('AssetSelect')).toEqual([
      'asset_management.cex_mapping.form.asset_non_empty',
    ]);
  });

  it.each([
    [null, true],
    ['kraken', false],
  ])('should read the switch off a payload whose location is %s', async (location, expected) => {
    wrapper = createWrapper({ ...baseModel(), location }, { forAllExchanges: !expected });
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.emitted('update:forAllExchanges')?.at(-1)).toEqual([expected]);
  });

  it('should write a cleared exchange back as null', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    // Null is what "every exchange" means in this payload, so unlike the counterparty mapping the
    // field is nullable on purpose.
    await edit('ExchangeInput', undefined);

    expect(lastModel().location).toBeNull();
  });

  it('should write an edited symbol back into the model', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await edit('RuiTextField', 'DAI');

    expect(lastModel().locationSymbol).toBe('DAI');
  });

  it('should flag stateUpdated once a field is edited', async () => {
    wrapper = createWrapper();
    // Settle the mounted work first, so what follows is the only edit in play.
    await vi.advanceTimersByTimeAsync(600);

    await edit('RuiTextField', 'DAI');

    expect(wrapper.emitted('update:stateUpdated')?.at(-1)).toEqual([true]);
  });

  it('should not flag stateUpdated before anything is edited', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersByTimeAsync(600);

    expect(wrapper.emitted('update:stateUpdated')?.at(-1)).not.toEqual([true]);
  });

  it('should lock everything but the asset while editing', async () => {
    wrapper = createWrapper(baseModel(), { editMode: true });
    await vi.advanceTimersToNextTimerAsync();

    expect(stub('RuiSwitch').props('disabled')).toBe(true);
    expect(stub('ExchangeInput').props('disabled')).toBe(true);
    expect(stub('RuiTextField').props('disabled')).toBe(true);
    expect(stub('AssetSelect').props('disabled')).toBeFalsy();
  });

  it('should lock the exchange while the mapping covers all of them', async () => {
    wrapper = createWrapper({ ...baseModel(), location: null }, { forAllExchanges: true });
    await vi.advanceTimersToNextTimerAsync();

    expect(stub('ExchangeInput').props('disabled')).toBe(true);
  });

  it.each([
    ['binance', 'binanceus'],
    ['coinbase', 'coinbaseprime'],
  ])('should point out that a %s mapping also covers %s', async (primary, related) => {
    wrapper = createWrapper({ ...baseModel(), location: primary }, { forAllExchanges: false });
    await vi.advanceTimersToNextTimerAsync();

    const shown = wrapper.findAllComponents({ name: 'LocationDisplay' });
    expect(shown.map(display => display.props('identifier'))).toEqual([primary, related]);
  });

  it('should say nothing about a related exchange for any other one', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.findAllComponents({ name: 'LocationDisplay' })).toHaveLength(0);
  });

  // Deliberately flipped in the zod swap. Vuelidate read external results through $errors, so a
  // rejected save said nothing at all on a field the user had not been in.
  it('should show a server error on an untouched field', async () => {
    const errorMessages: ValidationErrors = { locationSymbol: ['already mapped'] };
    wrapper = createWrapper(baseModel(), { errorMessages });
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('RuiTextField')).toEqual(['already mapped']);
  });
});
