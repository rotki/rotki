import type { BankAuthChallenge, BankConnection } from '@/modules/banks/types';
import { createTestBankConnection } from '@test/utils/create-data';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import BankSyncStatus from '@/modules/banks/components/BankSyncStatus.vue';
import '@test/i18n';

function createWrapper(syncStatus: Partial<BankConnection['syncStatus']> = {}): VueWrapper<InstanceType<typeof BankSyncStatus>> {
  return mount(BankSyncStatus, {
    global: {
      stubs: {
        RuiTooltip: { template: '<span><slot name="activator" /><span data-testid="tooltip"><slot /></span></span>' },
        TimeAgoDisplay: { props: ['timestamp'], template: '<span data-testid="time">{{ timestamp }}</span>' },
      },
    },
    props: { status: createTestBankConnection('fints', 'Main', syncStatus).syncStatus },
  });
}

function badges(wrapper: VueWrapper): string[] {
  return ['bank-auth-required', 'bank-auth-expired', 'bank-sync-error']
    .filter(id => wrapper.find(`[data-testid=${id}]`).exists());
}

describe('modules/banks/components/BankSyncStatus', () => {
  it('should show when the connection last synced, or that it never did, with no badge while healthy', () => {
    expect(createWrapper({ lastSyncTs: 1700000000 }).find('[data-testid=time]').text()).toBe('1700000000');
    const never = createWrapper();
    expect(never.text()).toBe('bank_settings.sync.never');
    expect(badges(never)).toEqual([]);
  });

  it('should show one badge, a pending authentication first, then an expired one, then a failed sync', () => {
    const everything = { authChallenge: createMock<BankAuthChallenge>(), authExpired: true, lastError: 'down' };
    expect(badges(createWrapper(everything))).toEqual(['bank-auth-required']);
    expect(badges(createWrapper({ authExpired: true, lastError: 'down' }))).toEqual(['bank-auth-expired']);
    expect(badges(createWrapper({ lastError: 'down' }))).toEqual(['bank-sync-error']);
  });

  it('should put a failed sync\'s message beside its badge and in full in the tooltip', () => {
    const wrapper = createWrapper({ lastError: 'The bank did not answer' });

    expect(wrapper.find('[data-testid=bank-sync-error-message]').text()).toBe('The bank did not answer');
    expect(wrapper.find('[data-testid=tooltip]').text()).toBe('The bank did not answer');
  });
});
