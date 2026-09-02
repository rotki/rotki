import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AccountFormApiKeyMenu from '@/modules/accounts/management/AccountFormApiKeyMenu.vue';

const RuiMenu = {
  template: '<div><slot name="activator" :attrs="{}" /><slot /></div>',
};

const dismissedNotices = ref<string[]>([]);
const updateFrontendSetting = vi.fn(async () => ({ success: true }));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn(() => dismissedNotices),
}));

vi.mock('@/modules/settings/use-frontend-settings-writer', () => ({
  useFrontendSettingsWriter: vi.fn(() => ({ updateFrontendSetting })),
}));

describe('accountFormApiKeyMenu', () => {
  let wrapper: VueWrapper | undefined;

  function create(service: 'beaconchain' | 'consensusRpc' | 'etherscan'): VueWrapper {
    wrapper = mount(AccountFormApiKeyMenu, {
      global: { stubs: { RuiMenu } },
      props: { service },
    });
    return wrapper;
  }

  beforeEach(() => {
    vi.clearAllMocks();
    set(dismissedNotices, []);
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
  });

  it('should head the guidance with the name of the service', () => {
    const content = create('beaconchain').find('[data-testid=api-key-menu-content]');

    expect(content.text()).toContain('external_services.beaconchain.title');
  });

  it('should head the consensus rpc case with its own title, having no service name of its own to borrow', () => {
    const content = create('consensusRpc').find('[data-testid=api-key-menu-content]');

    expect(content.text()).toContain('external_services.api_key_menu.consensus_rpc_title');
  });

  it('should show the guidance belonging to the given service', () => {
    const content = create('etherscan').find('[data-testid=api-key-menu-content]');

    expect(content.text()).toContain('external_services.etherscan.api_key_message');
  });

  it('should announce the trigger as a collapsed disclosure, which RuiMenu supplies no attribute for', () => {
    const trigger = create('beaconchain').find('[data-testid=api-key-menu-activator]');

    expect(trigger.attributes('aria-haspopup')).toBe('dialog');
    expect(trigger.attributes('aria-expanded')).toBe('false');
  });

  it('should label the panel as a dialog naming the service', () => {
    const panel = create('beaconchain').find('[data-testid=api-key-menu-content]');

    expect(panel.attributes('role')).toBe('dialog');
    expect(panel.attributes('aria-label')).toBe('external_services.beaconchain.title');
  });

  it('should persist the dismissal so it survives a reload', async () => {
    const view = create('beaconchain');
    await view.find('[data-testid=api-key-menu-dismiss]').trigger('click');
    await flushPromises();

    expect(updateFrontendSetting).toHaveBeenCalledWith({ dismissedApiKeyNotices: ['beaconchain'] });
  });

  it('should keep the dismissals of other services when dismissing one', async () => {
    set(dismissedNotices, ['etherscan']);

    const view = create('beaconchain');
    await view.find('[data-testid=api-key-menu-dismiss]').trigger('click');
    await flushPromises();

    expect(updateFrontendSetting).toHaveBeenCalledWith({ dismissedApiKeyNotices: ['etherscan', 'beaconchain'] });
  });

  it('should render nothing once the service has been dismissed', () => {
    set(dismissedNotices, ['beaconchain']);

    expect(create('beaconchain').find('[data-testid=api-key-menu-activator]').exists()).toBe(false);
  });

  it('should still render when a different service was dismissed', () => {
    set(dismissedNotices, ['etherscan']);

    expect(create('beaconchain').find('[data-testid=api-key-menu-activator]').exists()).toBe(true);
  });
});
