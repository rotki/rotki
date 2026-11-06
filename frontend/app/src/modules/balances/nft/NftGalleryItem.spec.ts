import type { GalleryNft } from '@/modules/assets/nfts';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import NftGalleryItem from '@/modules/balances/nft/NftGalleryItem.vue';

const { updateFrontendSetting, whitelisted } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    updateFrontendSetting: vi.fn<(payload: object) => Promise<{ success: boolean }>>(async () => Promise.resolve({ success: true })),
    whitelisted: ref<string[]>([]),
  };
});

vi.mock('@/modules/balances/nft/use-nft-image', async () => {
  const { computed, ref } = await import('vue');
  return {
    useNftImage: (): object => ({
      isVideo: ref<boolean>(false),
      renderedMedia: computed<string>(() => 'placeholder.svg'),
      shouldRender: computed<boolean>(() => false),
    }),
  };
});

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): object => whitelisted,
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): object => ({ updateFrontendSetting }),
}));

/** Opens through its activator and renders its content only while open, as the real menu does. */
const RuiMenu = defineComponent({
  emits: ['update:modelValue'],
  props: ['modelValue'],
  template: `<div>
    <slot name="activator" :attrs="{ onClick: () => $emit('update:modelValue', true) }" />
    <div v-if="modelValue"><slot /></div>
  </div>`,
});

function createWrapper(): VueWrapper {
  return mount(NftGalleryItem, {
    global: {
      stubs: {
        AppImage: true,
        AssetAmountDisplay: true,
        ExternalLink: { template: '<div><slot /></div>' },
        FiatDisplay: true,
        IconLink: true,
        RuiMenu,
      },
    },
    props: {
      item: createMock<GalleryNft>({
        backgroundColor: null,
        collection: null,
        imageUrl: 'https://cdn.example.com/nft/1.png',
        name: 'Punk',
        permalink: null,
      }),
    },
  });
}

describe('modules/balances/nft/NftGalleryItem', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should ask beside the unlock button before allowing the media domain', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=nft-allow-domain]').trigger('click');

    expect(wrapper.find('[data-testid=inline-confirm]').text()).toContain('general_settings.nft_setting.update_whitelist_confirmation.message');
    expect(updateFrontendSetting).not.toHaveBeenCalled();
  });

  it('should allow the media domain once the question is accepted', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=nft-allow-domain]').trigger('click');
    await wrapper.find('[data-testid=inline-confirm-accept]').trigger('click');

    expect(updateFrontendSetting).toHaveBeenCalledExactlyOnceWith({ whitelistedDomainsForNftImages: ['example.com'] });
  });

  it('should leave the whitelist alone when the question is cancelled', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=nft-allow-domain]').trigger('click');
    await wrapper.find('[data-testid=inline-confirm-cancel]').trigger('click');

    expect(updateFrontendSetting).not.toHaveBeenCalled();
    expect(wrapper.find('[data-testid=inline-confirm]').exists()).toBe(false);
  });
});
