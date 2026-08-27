import type { StubInstance } from '@test/utils/component-vm';
import { EvmTokenKind, type UnderlyingToken } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import UnderlyingTokenManager from '@/modules/assets/admin/UnderlyingTokenManager.vue';
import '@test/i18n';

const ADDRESS = '0x9531C059098e3d194fF87FebB587aB07B30B1306';
const OTHER_ADDRESS = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48';

function inputStub(name: string): Record<string, unknown> {
  return {
    emits: ['update:modelValue', 'blur'],
    name,
    props: ['modelValue', 'errorMessages', 'disabled'],
    template: '<div><slot name="append" /></div>',
  };
}

const stubs = {
  RowActions: {
    emits: ['delete-click', 'edit-click'],
    name: 'RowActions',
    template: '<div />',
  },
  RuiMenuSelect: inputStub('RuiMenuSelect'),
  RuiTextField: inputStub('RuiTextField'),
  SimpleTable: { name: 'SimpleTable', template: '<table><slot /></table>' },
  UnderlyingTokenWeightHint: true,
};

describe('underlyingTokenManager', () => {
  let wrapper: VueWrapper<InstanceType<typeof UnderlyingTokenManager>>;

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.useRealTimers();
  });

  function createWrapper(modelValue: UnderlyingToken[] = []): VueWrapper<InstanceType<typeof UnderlyingTokenManager>> {
    return mount(UnderlyingTokenManager, {
      global: { stubs },
      props: { modelValue },
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

  function addDisabled(): unknown {
    return wrapper.findComponent<StubInstance>('[data-testid=underlying-token-add]').props('disabled');
  }

  async function typeWithoutBlurring(testId: string, value: string): Promise<void> {
    field(testId).vm.$emit('update:modelValue', value);
    await vi.advanceTimersToNextTimerAsync();
  }

  async function edit(testId: string, value: string): Promise<void> {
    const input = field(testId);
    input.vm.$emit('update:modelValue', value);
    input.vm.$emit('blur');
    await vi.advanceTimersToNextTimerAsync();
  }

  async function fillRow(address = ADDRESS, weight = '50'): Promise<void> {
    await edit('underlying-token-address', address);
    await edit('underlying-token-weight', weight);
  }

  async function add(): Promise<void> {
    await wrapper.find('form').trigger('submit');
    await vi.advanceTimersToNextTimerAsync();
  }

  function lastModel(): UnderlyingToken[] | undefined {
    return wrapper.emitted<[UnderlyingToken[]]>('update:modelValue')?.at(-1)?.[0];
  }

  it('should show no message before the staging row is touched', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(messages('underlying-token-address')).toEqual([]);
    expect(messages('underlying-token-weight')).toEqual([]);
  });

  it('should block the add button while the staging row is empty', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(addDisabled()).toBe(true);
  });

  it('should allow the add once the row is valid', async () => {
    wrapper = createWrapper();
    await fillRow();

    expect(addDisabled()).toBe(false);
    expect(messages('underlying-token-address')).toEqual([]);
    expect(messages('underlying-token-weight')).toEqual([]);
  });

  it('should report an emptied address as both missing and malformed', async () => {
    wrapper = createWrapper();
    await fillRow();

    await edit('underlying-token-address', '');

    expect(messages('underlying-token-address')).toEqual([
      'underlying_token_manager.validation.valid',
      'underlying_token_manager.validation.address_non_empty',
    ]);
  });

  it('should report a malformed address on its own', async () => {
    wrapper = createWrapper();
    await fillRow('0x123');

    expect(messages('underlying-token-address')).toEqual(['underlying_token_manager.validation.valid']);
    expect(addDisabled()).toBe(true);
  });

  it('should report an emptied weight as missing only', async () => {
    wrapper = createWrapper();
    await fillRow();

    await edit('underlying-token-weight', '');

    expect(messages('underlying-token-weight')).toEqual(['underlying_token_manager.validation.non_empty']);
  });

  it('should report an out-of-range weight while typing, before the field is left', async () => {
    wrapper = createWrapper();
    await edit('underlying-token-address', ADDRESS);

    await typeWithoutBlurring('underlying-token-weight', '150');

    expect(messages('underlying-token-weight')).toEqual(['underlying_token_manager.validation.out_of_range']);
  });

  it.each([
    ['0'],
    ['101'],
  ])('should reject %s as out of range', async (weight) => {
    wrapper = createWrapper();
    await fillRow(ADDRESS, weight);

    expect(messages('underlying-token-weight')).toEqual(['underlying_token_manager.validation.out_of_range']);
    expect(addDisabled()).toBe(true);
  });

  it('should report a non-numeric weight as both out of range and not a number', async () => {
    wrapper = createWrapper();
    await fillRow(ADDRESS, 'abc');

    expect(messages('underlying-token-weight')).toEqual([
      'underlying_token_manager.validation.out_of_range',
      'underlying_token_manager.validation.not_valid',
    ]);
  });

  it('should accept a fractional weight inside the range', async () => {
    wrapper = createWrapper();
    await fillRow(ADDRESS, '12.5');

    expect(messages('underlying-token-weight')).toEqual([]);
    expect(addDisabled()).toBe(false);
  });

  it('should reject a weight padded with whitespace', async () => {
    wrapper = createWrapper();
    await fillRow(ADDRESS, ' 50');

    expect(messages('underlying-token-weight')).toEqual([
      'underlying_token_manager.validation.out_of_range',
      'underlying_token_manager.validation.not_valid',
    ]);
  });

  it('should append the staged token and clear the row', async () => {
    wrapper = createWrapper();
    await fillRow();

    await add();

    expect(lastModel()).toEqual([{ address: ADDRESS, tokenKind: EvmTokenKind.ERC20, weight: '50' }]);
    expect(field('underlying-token-address').props('modelValue')).toBe('');
    expect(field('underlying-token-weight').props('modelValue')).toBe('');
    expect(messages('underlying-token-address')).toEqual([]);
  });

  it('should replace an entry whose address is staged again', async () => {
    wrapper = createWrapper([{ address: ADDRESS, tokenKind: EvmTokenKind.ERC20, weight: '20' }]);
    await fillRow(ADDRESS, '70');

    await add();

    expect(lastModel()).toEqual([{ address: ADDRESS, tokenKind: EvmTokenKind.ERC20, weight: '70' }]);
  });

  it('should keep both entries when a second address is staged', async () => {
    wrapper = createWrapper([{ address: ADDRESS, tokenKind: EvmTokenKind.ERC20, weight: '20' }]);
    await fillRow(OTHER_ADDRESS, '70');

    await add();

    expect(lastModel()).toHaveLength(2);
    expect(lastModel()?.at(-1)?.address).toBe(OTHER_ADDRESS);
  });

  it('should move a row back into the staging fields when it is edited', async () => {
    wrapper = createWrapper([{ address: ADDRESS, tokenKind: EvmTokenKind.ERC20, weight: '20' }]);
    await vi.advanceTimersToNextTimerAsync();

    wrapper.findComponent<StubInstance>({ name: 'RowActions' }).vm.$emit('edit-click', {
      address: ADDRESS,
      tokenKind: EvmTokenKind.ERC20,
      weight: '20',
    });
    await vi.advanceTimersToNextTimerAsync();

    expect(field('underlying-token-address').props('modelValue')).toBe(ADDRESS);
    expect(field('underlying-token-weight').props('modelValue')).toBe('20');
    expect(lastModel()).toEqual([]);
  });

  it('should drop a row when it is deleted', async () => {
    wrapper = createWrapper([{ address: ADDRESS, tokenKind: EvmTokenKind.ERC20, weight: '20' }]);
    await vi.advanceTimersToNextTimerAsync();

    wrapper.findComponent<StubInstance>({ name: 'RowActions' }).vm.$emit('delete-click');
    await vi.advanceTimersToNextTimerAsync();

    expect(lastModel()).toEqual([]);
  });

  it('should keep its permanently invalid staging row to itself', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    expect(addDisabled()).toBe(true);
    expect('validate' in wrapper.vm).toBe(false);
    expect(wrapper.emitted('update:valid')).toBeUndefined();
  });
});
