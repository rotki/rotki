import { type DOMWrapper, flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, ref } from 'vue';
import DetectTokenChainsSelection from '@/modules/accounts/balances/DetectTokenChainsSelection.vue';

const selected = ref<string[]>([]);
const isDetectingTokens = ref<boolean>(false);
const allChains = ['eth', 'optimism', 'base'];
const detectChains = vi.fn(async (_chain?: string): Promise<boolean> => false);
const reset = vi.fn((): void => {
  set(selected, []);
});
const toggle = vi.fn((chain?: string): void => {
  if (!chain)
    set(selected, get(selected).length === allChains.length ? [] : [...allChains]);
  else if (get(selected).includes(chain))
    set(selected, get(selected).filter(item => item !== chain));
  else
    set(selected, [...get(selected), chain]);
});

vi.mock('@/modules/accounts/balances/use-detect-token-chains-selection', () => ({
  useDetectTokenChainsSelection: vi.fn(() => ({
    detectChains,
    filtered: computed(() => allChains.map(id => ({ id, name: id }))),
    hasSelection: computed<boolean>(() => get(selected).length > 0),
    isAllSelected: computed<boolean>(() => get(selected).length === allChains.length),
    isDetectingTokens: computed<boolean>(() => get(isDetectingTokens)),
    isSelected: (chain: string): boolean => get(selected).includes(chain),
    reset,
    selectedCount: computed<number>(() => get(selected).length),
    toggle,
  })),
}));

const stubs = {
  DetectTokensChainsSelectionItem: {
    emits: ['toggle', 'detect'],
    props: {
      allowRedetect: { default: false, type: Boolean },
      detecting: { default: false, type: Boolean },
      enabled: { default: false, type: Boolean },
      item: { required: true, type: Object },
    },
    template: `<div data-testid="chain-item" :data-chain="item.id" :data-enabled="enabled" :data-allow-redetect="allowRedetect" :data-detecting="detecting">
      <button data-testid="chain-detect" @click.stop="$emit('detect', item.id)" />
    </div>`,
  },
  RuiButton: {
    inheritAttrs: false,
    props: { disabled: { default: false, type: Boolean }, loading: { default: false, type: Boolean } },
    template: '<button v-bind="$attrs" :disabled="disabled" :data-loading="loading"><slot /></button>',
  },
  RuiCheckbox: {
    props: {
      disabled: { default: false, type: Boolean },
      indeterminate: { default: false, type: Boolean },
      modelValue: { default: false, type: Boolean },
    },
    template: '<label data-testid="select-all" :data-disabled="disabled" :data-indeterminate="indeterminate" :data-checked="modelValue"><slot /></label>',
  },
  RuiTextField: {
    emits: ['update:modelValue'],
    props: { modelValue: { default: '', type: String } },
    template: '<input data-testid="search" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
  },
};

function createWrapper(): VueWrapper<InstanceType<typeof DetectTokenChainsSelection>> {
  return mount(DetectTokenChainsSelection, { global: { stubs } });
}

function redetectButton(wrapper: VueWrapper): DOMWrapper<HTMLButtonElement> {
  const button = wrapper.findAll('button').find(item => item.text().startsWith('account_balances.detect_tokens.selection.redetect_selected'));
  if (!button)
    throw new Error('the re-detect button is missing');
  return button;
}

function cancelButton(wrapper: VueWrapper): DOMWrapper<HTMLButtonElement> | undefined {
  return wrapper.findAll('button').find(button => button.text() === 'common.actions.cancel');
}

describe('modules/accounts/balances/DetectTokenChainsSelection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(selected, []);
    set(isDetectingTokens, false);
    detectChains.mockResolvedValue(false);
  });

  it('should list every chain and toggle one when its row is clicked', async () => {
    const wrapper = createWrapper();
    const items = wrapper.findAll('[data-testid=chain-item]');

    expect(items.map(item => item.attributes('data-chain'))).toEqual(allChains);

    items.at(1)?.element.parentElement?.click();
    await nextTick();

    expect(toggle).toHaveBeenCalledWith('optimism');
    expect(wrapper.find('[data-chain=optimism]').attributes('data-enabled')).toBe('true');
  });

  it('should offer a single chain re-detect only while nothing is selected', async () => {
    const wrapper = createWrapper();
    expect(wrapper.find('[data-chain=eth]').attributes('data-allow-redetect')).toBe('true');

    set(selected, ['eth']);
    await nextTick();

    expect(wrapper.find('[data-chain=eth]').attributes('data-allow-redetect')).toBe('false');
  });

  it('should re-detect a single chain from its row without closing the menu', async () => {
    const wrapper = createWrapper();
    await wrapper.find('[data-chain=base] [data-testid=chain-detect]').trigger('click');
    await flushPromises();

    expect(detectChains).toHaveBeenCalledWith('base');
    expect(wrapper.emitted('done')).toBeUndefined();
    expect(wrapper.emitted('redetect:all')).toBeUndefined();
  });

  it('should keep the re-detect button off until a chain is selected, and count the selection', async () => {
    const wrapper = createWrapper();
    expect(redetectButton(wrapper).attributes('disabled')).toBeDefined();
    expect(cancelButton(wrapper)).toBeUndefined();

    set(selected, ['eth', 'base']);
    await nextTick();

    expect(redetectButton(wrapper).attributes('disabled')).toBeUndefined();
    expect(redetectButton(wrapper).text()).toBe('account_balances.detect_tokens.selection.redetect_selected::2');
  });

  it('should re-detect the selection and report done', async () => {
    set(selected, ['eth']);
    const wrapper = createWrapper();
    await redetectButton(wrapper).trigger('click');
    await flushPromises();

    expect(detectChains).toHaveBeenCalledWith(undefined);
    expect(wrapper.emitted('done')).toEqual([[]]);
    expect(wrapper.emitted('redetect:all')).toBeUndefined();
  });

  it('should hand a selection of every chain to the full re-detect instead', async () => {
    detectChains.mockResolvedValue(true);
    set(selected, [...allChains]);
    const wrapper = createWrapper();
    await redetectButton(wrapper).trigger('click');
    await flushPromises();

    expect(wrapper.emitted('redetect:all')).toEqual([[]]);
    expect(wrapper.emitted('done')).toBeUndefined();
  });

  it('should clear the selection from cancel', async () => {
    set(selected, ['eth']);
    const wrapper = createWrapper();
    await cancelButton(wrapper)?.trigger('click');

    expect(reset).toHaveBeenCalledOnce();
    expect(cancelButton(wrapper)).toBeUndefined();
  });

  it('should toggle every chain from select all and show a partial selection as indeterminate', async () => {
    const wrapper = createWrapper();
    const selectAll = wrapper.find('[data-testid=select-all]');
    expect(selectAll.attributes('data-indeterminate')).toBe('false');

    set(selected, ['eth']);
    await nextTick();
    expect(selectAll.attributes('data-indeterminate')).toBe('true');

    await selectAll.trigger('click');

    expect(toggle).toHaveBeenCalledWith();
    expect(selectAll.attributes('data-checked')).toBe('true');
    expect(selectAll.attributes('data-indeterminate')).toBe('false');
  });

  it('should clear the selection when the search changes', async () => {
    set(selected, ['eth']);
    const wrapper = createWrapper();
    await wrapper.find('[data-testid=search]').setValue('opt');

    expect(reset).toHaveBeenCalledOnce();
  });

  it('should hold everything off while tokens are being detected', async () => {
    set(selected, ['eth']);
    const wrapper = createWrapper();
    set(isDetectingTokens, true);
    await nextTick();

    expect(wrapper.find('[data-testid=select-all]').attributes('data-disabled')).toBe('true');
    expect(redetectButton(wrapper).attributes('data-loading')).toBe('true');
    expect(wrapper.find('[data-chain=eth]').attributes('data-detecting')).toBe('true');
  });
});
