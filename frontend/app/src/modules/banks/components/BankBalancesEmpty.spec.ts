import type { BankManifest } from '@/modules/banks/types';
import { createMock } from '@test/utils/create-mock';
import { createCustomPinia } from '@test/utils/create-pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import BankBalancesEmpty from '@/modules/banks/components/BankBalancesEmpty.vue';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import '@test/i18n';

const qonto = createMock<BankManifest>({ connector: 'qonto', displayName: 'Qonto' });

function createWrapper(): VueWrapper<InstanceType<typeof BankBalancesEmpty>> {
  return mount(BankBalancesEmpty, {
    global: { stubs: { BankConnectorIcon: true } },
  });
}

describe('modules/banks/components/BankBalancesEmpty', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
  });

  it('should disable adding a bank while no supported bank is known', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=bank-balances-empty-connect]').attributes('disabled')).toBeDefined();
    expect(wrapper.find('[data-testid=bank-balances-empty-shortcut]').exists()).toBe(false);
  });

  it('should add a bank, or the bank picked from the supported ones, once they are known', async () => {
    useBankConnectionsStore().setManifests([qonto]);
    const wrapper = createWrapper();

    const add = wrapper.find('[data-testid=bank-balances-empty-connect]');
    expect(add.attributes('disabled')).toBeUndefined();
    await add.trigger('click');
    await wrapper.find('[data-testid=bank-balances-empty-shortcut][data-bank=qonto]').trigger('click');

    expect(wrapper.emitted('connect')).toEqual([[], ['qonto']]);
  });
});
