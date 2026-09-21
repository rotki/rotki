import type { BankConnection, BankConnectionIdentity } from '@/modules/banks/types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import HistoryRefreshBanks from '@/modules/history/refresh/HistoryRefreshBanks.vue';
import '@test/i18n';

const main: BankConnectionIdentity = { identifier: 'c1', location: 'qonto', name: 'rotki Solutions GmbH' };
const side: BankConnectionIdentity = { identifier: 'c2', location: 'qonto', name: 'Side organization' };

function connection(identity: BankConnectionIdentity): BankConnection {
  return { ...identity, connector: 'qonto', displayName: 'Qonto', syncStatus: { authChallenge: null, lastError: null, lastSyncTs: null, running: false } };
}

describe('historyRefreshBanks', () => {
  let pinia: Pinia;

  function createWrapper(props: { modelValue?: BankConnectionIdentity[]; search?: string } = {}): VueWrapper<InstanceType<typeof HistoryRefreshBanks>> {
    return mount(HistoryRefreshBanks, {
      global: {
        plugins: [pinia],
        stubs: { LocationDisplay: true },
      },
      props: { modelValue: props.modelValue ?? [], processing: false, search: props.search ?? '' },
    });
  }

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
    useBankConnectionsStore().setConnections([connection(main), connection(side)]);
  });

  it('should render one row per bank connection', () => {
    const rows = createWrapper().findAll('[data-testid=refresh-bank-row]');
    expect(rows).toHaveLength(2);
    expect(rows[0].text()).toContain(main.name);
    expect(rows[1].text()).toContain(side.name);
  });

  it('should select a connection from its row and report that not every connection is picked', async () => {
    const wrapper = createWrapper();
    await wrapper.findAll('[data-testid=refresh-bank-row]')[1].trigger('click');
    expect(wrapper.emitted('update:modelValue')).toEqual([[[side]]]);
    expect(wrapper.emitted('update:all-selected')).toEqual([[false]]);
  });

  it('should unselect a picked connection when its row is clicked again', async () => {
    const wrapper = createWrapper({ modelValue: [main, side] });
    await wrapper.findAll('[data-testid=refresh-bank-row]')[0].trigger('click');
    expect(wrapper.emitted('update:modelValue')).toEqual([[[side]]]);
  });

  it('should filter the rows by connection name', () => {
    const rows = createWrapper({ search: 'side' }).findAll('[data-testid=refresh-bank-row]');
    expect(rows).toHaveLength(1);
    expect(rows[0].text()).toContain(side.name);
  });

  it('should pick every connection through select all and report the selection as complete', () => {
    const wrapper = createWrapper();
    wrapper.vm.toggleSelectAll();
    expect(wrapper.emitted('update:modelValue')).toEqual([[[main, side]]]);
    expect(wrapper.emitted('update:all-selected')).toEqual([[true]]);
  });

  it('should explain that nothing can be refreshed when no bank is connected', () => {
    useBankConnectionsStore().setConnections([]);
    const wrapper = createWrapper();
    expect(wrapper.findAll('[data-testid=refresh-bank-row]')).toHaveLength(0);
    expect(wrapper.text()).toContain('history_refresh_selection.no_banks');
  });
});
