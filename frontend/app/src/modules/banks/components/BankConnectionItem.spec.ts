import type { BankAuthChallenge, BankConnection } from '@/modules/banks/types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import BankConnectionItem from '@/modules/banks/components/BankConnectionItem.vue';

const push = vi.fn(async (): Promise<void> => {});

vi.mock('vue-router', () => ({
  useRouter: (): { push: typeof push } => ({ push }),
}));

const challenge: BankAuthChallenge = {
  challenge: null,
  challengeData: null,
  challengeHtml: null,
  challengeMimeType: null,
  primitive: 'otp input',
  prompt: 'Enter the TAN',
};

const stubs = {
  LocationIcon: true,
  RuiButton: { template: '<button data-testid="bank-balances-connection-action"><slot /></button>' },
  RuiIcon: true,
  TimeAgoDisplay: true,
};

function connection(syncStatus: Partial<BankConnection['syncStatus']> = {}): BankConnection {
  return {
    displayName: 'Sparkasse',
    location: 'fints',
    name: 'main',
    syncStatus: { authChallenge: null, authExpired: false, lastError: null, lastSyncTs: null, running: false, ...syncStatus },
  };
}

function createWrapper(value: BankConnection): VueWrapper<InstanceType<typeof BankConnectionItem>> {
  return mount(BankConnectionItem, { global: { stubs }, props: { connection: value } });
}

describe('modules/banks/components/BankConnectionItem', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should show when a healthy connection last synced, with nothing to act on', () => {
    const wrapper = createWrapper(connection({ lastSyncTs: 1700000000 }));

    expect(wrapper.find('[data-testid=bank-balances-connection]').attributes('data-state')).toBe('ok');
    expect(wrapper.find('[data-testid=bank-balances-connection-synced]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=bank-balances-connection-status]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=bank-balances-connection-action]').exists()).toBe(false);
  });

  it('should leave out the sync time for a connection that never synced', () => {
    const wrapper = createWrapper(connection());

    expect(wrapper.find('[data-testid=bank-balances-connection-synced]').exists()).toBe(false);
  });

  it('should show the error of a failed connection and send it to review', async () => {
    const wrapper = createWrapper(connection({ lastError: 'Login refused', lastSyncTs: 1700000000 }));

    expect(wrapper.find('[data-testid=bank-balances-connection]').attributes('data-state')).toBe('failed');
    expect(wrapper.find('[data-testid=bank-balances-connection-status]').text()).toBe('bank_balances.status.failed::Login refused');
    expect(wrapper.find('[data-testid=bank-balances-connection-synced]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=bank-balances-connection-action]').text()).toBe('bank_balances.status.review');

    await wrapper.find('[data-testid=bank-balances-connection-action]').trigger('click');

    expect(push).toHaveBeenCalledWith({ name: '/api-keys/banks/', query: {} });
  });

  it('should ask for authentication and open it for this connection', async () => {
    const wrapper = createWrapper(connection({ authChallenge: challenge }));

    expect(wrapper.find('[data-testid=bank-balances-connection]').attributes('data-state')).toBe('authentication');
    expect(wrapper.find('[data-testid=bank-balances-connection-status]').text()).toBe('bank_balances.status.authentication');
    expect(wrapper.find('[data-testid=bank-balances-connection-action]').text()).toBe('bank_balances.status.authenticate');

    await wrapper.find('[data-testid=bank-balances-connection-action]').trigger('click');

    expect(push).toHaveBeenCalledWith({ name: '/api-keys/banks/', query: { authenticate: 'main', location: 'fints' } });
  });

  it('should say an expired TAN needs a new sync instead of showing the last sync time, and ask for that sync', async () => {
    const wrapper = createWrapper(connection({ authExpired: true, lastError: 'Login refused', lastSyncTs: 1700000000 }));

    expect(wrapper.find('[data-testid=bank-balances-connection]').attributes('data-state')).toBe('expired');
    expect(wrapper.find('[data-testid=bank-balances-connection-status]').text()).toBe('bank_balances.status.expired');
    expect(wrapper.find('[data-testid=bank-balances-connection-synced]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=bank-balances-connection-action]').text()).toBe('bank_settings.authentication.sync_again');

    await wrapper.find('[data-testid=bank-balances-connection-action]').trigger('click');

    expect(wrapper.emitted('sync')).toEqual([[{ location: 'fints', name: 'main' }]]);
    expect(push).not.toHaveBeenCalled();
  });

  it('should put a pending authentication ahead of an older failure', () => {
    const wrapper = createWrapper(connection({ authChallenge: challenge, lastError: 'Login refused' }));

    expect(wrapper.find('[data-testid=bank-balances-connection]').attributes('data-state')).toBe('authentication');
  });
});
