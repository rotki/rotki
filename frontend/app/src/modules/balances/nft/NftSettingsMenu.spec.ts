import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import NftSettingsMenu from '@/modules/balances/nft/NftSettingsMenu.vue';
import { Module } from '@/modules/core/common/modules';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';

const fetchQueriedAddresses = vi.fn(async (): Promise<void> => {});

vi.mock('@/modules/accounts/use-queried-address-operations', () => ({
  useQueriedAddressOperations: vi.fn(() => ({ fetchQueriedAddresses })),
}));

const stubs = {
  ExternalLink: true,
  NftImageRenderingSetting: { template: '<div data-testid="image-rendering-setting" />' },
  QueriedAddressDialog: {
    emits: ['close'],
    props: { module: { required: true, type: String } },
    template: '<div data-testid="queried-address-dialog" :data-module="module"><button data-testid="dialog-close" @click="$emit(\'close\')" /></div>',
  },
  RuiButton: {
    inheritAttrs: false,
    template: '<button v-bind="$attrs"><slot /></button>',
  },
  RuiDivider: true,
  RuiIcon: true,
  RuiMenu: {
    emits: ['update:modelValue'],
    props: { modelValue: { default: false, type: Boolean } },
    template: '<div data-testid="menu" :data-open="modelValue"><slot name="activator" :attrs="{ onClick: () => $emit(\'update:modelValue\', true) }" /><div><slot /></div></div>',
  },
  RuiTooltip: { template: '<div><slot name="activator" /></div>' },
};

function createWrapper(): VueWrapper<InstanceType<typeof NftSettingsMenu>> {
  return mount(NftSettingsMenu, { global: { stubs } });
}

describe('modules/balances/nft/NftSettingsMenu', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('should fetch the queried addresses when mounted', () => {
    createWrapper();

    expect(fetchQueriedAddresses).toHaveBeenCalledOnce();
  });

  it('should say every address is queried when none is listed for NFTs', () => {
    const { queriedAddresses } = storeToRefs(useSessionMetadataStore());
    set(queriedAddresses, { makerdaoDsr: ['0x1', '0x2'] });
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=nft-settings-addresses]').text()).toContain('nft_settings.addresses.all');
  });

  it('should count the addresses listed for NFTs', () => {
    const { queriedAddresses } = storeToRefs(useSessionMetadataStore());
    set(queriedAddresses, { nfts: ['0x1', '0x2'] });
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=nft-settings-addresses]').text()).toContain('nft_settings.addresses.some::2');
  });

  it('should close the menu and open the address dialog for the NFT module', async () => {
    const wrapper = createWrapper();
    await wrapper.find('[data-testid=nft-settings]').trigger('click');
    expect(wrapper.find('[data-testid=menu]').attributes('data-open')).toBe('true');
    expect(wrapper.find('[data-testid=queried-address-dialog]').exists()).toBe(false);

    await wrapper.find('[data-testid=nft-settings-manage-addresses]').trigger('click');

    expect(wrapper.find('[data-testid=menu]').attributes('data-open')).toBe('false');
    expect(wrapper.find('[data-testid=queried-address-dialog]').attributes('data-module')).toBe(Module.NFTS);
  });

  it('should remove the address dialog once it closes', async () => {
    const wrapper = createWrapper();
    await wrapper.find('[data-testid=nft-settings-manage-addresses]').trigger('click');
    await wrapper.find('[data-testid=dialog-close]').trigger('click');

    expect(wrapper.find('[data-testid=queried-address-dialog]').exists()).toBe(false);
  });

  it('should keep the image rendering setting in the menu', () => {
    const wrapper = createWrapper();

    expect(wrapper.find('[data-testid=nft-settings-images] [data-testid=image-rendering-setting]').exists()).toBe(true);
  });
});
