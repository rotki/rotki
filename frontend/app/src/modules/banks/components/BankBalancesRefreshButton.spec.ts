import type { BankConnectionIdentity } from '@/modules/banks/types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import BankBalancesRefreshButton from '@/modules/banks/components/BankBalancesRefreshButton.vue';

const stubs = {
  BankLabel: { props: ['name'], template: '<span>{{ name }}</span>' },
  RuiButton: {
    inheritAttrs: false,
    props: { disabled: { default: false, type: Boolean }, loading: { default: false, type: Boolean } },
    template: '<button v-bind="$attrs" :disabled="disabled" :data-loading="loading"><slot /></button>',
  },
  RuiButtonGroup: { template: '<div><slot /></div>' },
  RuiDivider: true,
  RuiIcon: true,
  RuiMenu: {
    emits: ['update:modelValue'],
    props: { modelValue: { default: false, type: Boolean } },
    template: '<div data-testid="menu" :data-open="modelValue"><slot name="activator" :attrs="{ onClick: () => $emit(\'update:modelValue\', true) }" /><div><slot /></div></div>',
  },
  RuiTooltip: { template: '<div><slot name="activator" /><span data-testid="tooltip"><slot /></span></div>' },
};

const dkb: BankConnectionIdentity = { connector: 'fints', name: 'DKB' };
const ing: BankConnectionIdentity = { connector: 'fints', name: 'ING' };

interface WrapperProps {
  banks?: BankConnectionIdentity[];
  selected?: string;
  loading?: boolean;
  isBankLoading?: (name: string) => boolean;
}

function createWrapper(props: WrapperProps = {}): VueWrapper<InstanceType<typeof BankBalancesRefreshButton>> {
  return mount(BankBalancesRefreshButton, {
    global: { stubs },
    props: { banks: [dkb, ing], isBankLoading: (): boolean => props.loading ?? false, ...props },
  });
}

async function openMenu(wrapper: VueWrapper): Promise<void> {
  await wrapper.find('[data-testid=refresh-bank-balances-menu]').trigger('click');
  expect(wrapper.find('[data-testid=menu]').attributes('data-open')).toBe('true');
}

describe('modules/banks/components/BankBalancesRefreshButton', () => {
  it('should ask for a refresh of what is in view from the main button', async () => {
    const wrapper = createWrapper();
    await wrapper.find('[data-testid=refresh-bank-balances]').trigger('click');

    expect(wrapper.emitted('refresh')).toEqual([[]]);
  });

  it('should say every bank is refreshed when none is selected, and name the selected one otherwise', () => {
    expect(createWrapper().find('[data-testid=tooltip]').text()).toBe('bank_balances.refresh_menu.all');
    expect(createWrapper({ selected: 'DKB' }).find('[data-testid=tooltip]').text()).toBe('bank_balances.refresh_menu.bank::DKB');
  });

  it('should refresh every bank from the menu and close it', async () => {
    const wrapper = createWrapper({ selected: 'DKB' });
    await openMenu(wrapper);
    await wrapper.find('[data-testid=refresh-bank-menu-all]').trigger('click');

    expect(wrapper.emitted('refresh-all')).toEqual([[]]);
    expect(wrapper.emitted('refresh')).toBeUndefined();
    expect(wrapper.find('[data-testid=menu]').attributes('data-open')).toBe('false');
  });

  it('should list each bank in the menu and refresh only the one picked', async () => {
    const wrapper = createWrapper();
    await openMenu(wrapper);
    const items = wrapper.findAll('[data-testid=refresh-bank-menu-item]');

    expect(items.map(item => item.attributes('data-bank'))).toEqual(['DKB', 'ING']);

    await items[1].trigger('click');
    expect(wrapper.emitted('refresh-bank')).toEqual([[ing]]);
    expect(wrapper.emitted('refresh-all')).toBeUndefined();
  });

  it('should not offer a second refresh while one runs', async () => {
    const wrapper = createWrapper({ loading: true });
    await openMenu(wrapper);

    expect(wrapper.find('[data-testid=refresh-bank-balances]').attributes('data-loading')).toBe('true');
    expect(wrapper.find('[data-testid=refresh-bank-menu-all]').attributes('disabled')).toBeDefined();
    expect(wrapper.findAll('[data-testid=refresh-bank-menu-item]').every(item => item.attributes('disabled') !== undefined)).toBe(true);
  });

  it('should keep the other banks and every bank refreshable while one bank refreshes on its own', async () => {
    const wrapper = createWrapper({ isBankLoading: name => name === 'DKB' });
    await openMenu(wrapper);
    const items = wrapper.findAll('[data-testid=refresh-bank-menu-item]');

    expect(wrapper.find('[data-testid=refresh-bank-balances]').attributes('data-loading')).toBe('false');
    expect(wrapper.find('[data-testid=refresh-bank-menu-all]').attributes('disabled')).toBeUndefined();
    expect(items.map(item => [item.attributes('data-bank'), item.attributes('disabled') !== undefined])).toEqual([['DKB', true], ['ING', false]]);
  });

  it('should show the main button busy while the selected bank refreshes', () => {
    const wrapper = createWrapper({ isBankLoading: name => name === 'DKB', selected: 'DKB' });
    expect(wrapper.find('[data-testid=refresh-bank-balances]').attributes('data-loading')).toBe('true');
  });
});
