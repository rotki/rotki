import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AccountFormApiKeyOffer from '@/modules/accounts/management/AccountFormApiKeyOffer.vue';

const dismissedNotices = ref<string[]>([]);
const updateFrontendSetting = vi.fn(async () => ({ success: true }));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn(() => dismissedNotices),
}));

vi.mock('@/modules/settings/use-frontend-settings-writer', () => ({
  useFrontendSettingsWriter: vi.fn(() => ({ updateFrontendSetting })),
}));

describe('accountFormApiKeyOffer', () => {
  let wrapper: VueWrapper | undefined;

  function create(service: 'beaconchain' | 'consensusRpc' | 'etherscan'): VueWrapper {
    wrapper = mount(AccountFormApiKeyOffer, {
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
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

  it('should head the offer with the name of the service', () => {
    expect(create('beaconchain').text()).toContain('external_services.beaconchain.title');
  });

  it('should head the consensus rpc case with its own title, having no service name of its own to borrow', () => {
    expect(create('consensusRpc').text()).toContain('external_services.api_key_menu.consensus_rpc_title');
  });

  it('should show the guidance belonging to the given service', () => {
    expect(create('etherscan').text()).toContain('external_services.etherscan.api_key_message');
  });

  it('should persist putting the reminder away, so it survives a reload', async () => {
    const view = create('beaconchain');
    await view.find('[data-testid=api-key-offer-dismiss]').trigger('click');
    await flushPromises();

    expect(updateFrontendSetting).toHaveBeenCalledWith({ dismissedApiKeyNotices: ['beaconchain'] });
  });

  // The section stays in the settings menu for good; only the reminder button goes.
  it('should keep the offer but drop the reminder button once put away', () => {
    set(dismissedNotices, ['beaconchain']);
    const view = create('beaconchain');

    expect(view.find('[data-testid=api-key-offer]').exists()).toBe(true);
    expect(view.find('[data-testid=api-key-offer-dismiss]').exists()).toBe(false);
  });
});
