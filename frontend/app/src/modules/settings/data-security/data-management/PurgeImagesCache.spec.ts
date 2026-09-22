import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { PurgeableImageCache } from '@/modules/session/purge';
import PurgeImagesCache from '@/modules/settings/data-security/data-management/PurgeImagesCache.vue';
import ActionStatusIndicator from '@/modules/shell/components/error/ActionStatusIndicator.vue';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';

const { spies } = vi.hoisted(() => ({
  spies: {
    clearEnsAvatarCache: vi.fn<(listEns: string[] | null) => Promise<boolean>>(),
    clearIconCache: vi.fn<(assets: string[] | null) => Promise<boolean>>(),
    refreshAvatarTimestamp: vi.fn<() => void>(),
    setLastRefreshedAssetIcon: vi.fn<() => void>(),
  },
}));

vi.mock('@/modules/assets/api/use-asset-icon-api', () => ({
  useAssetIconApi: (): object => ({ clearIconCache: spies.clearIconCache }),
}));

vi.mock('@/modules/accounts/address-book/use-addresses-names-api', () => ({
  useAddressesNamesApi: (): object => ({ clearEnsAvatarCache: spies.clearEnsAvatarCache }),
}));

vi.mock('@/modules/accounts/address-book/use-address-name-resolution', () => ({
  useAddressNameResolution: (): object => ({
    refreshAvatarTimestamp: spies.refreshAvatarTimestamp,
    useEnsNamesList: (): Ref<string[]> => ref(['vitalik.eth', 'rotki.eth']),
  }),
}));

vi.mock('@/modules/assets/use-assets-store', () => ({
  useAssetsStore: (): object => ({ setLastRefreshedAssetIcon: spies.setLastRefreshedAssetIcon }),
}));

const BUTTON = '[data-testid=purge-images-cache-button]';

describe('purgeImagesCache', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<InstanceType<typeof PurgeImagesCache>>;

  function createWrapper(): VueWrapper<InstanceType<typeof PurgeImagesCache>> {
    return mount(PurgeImagesCache, {
      global: {
        plugins: [pinia],
        stubs: {
          ActionStatusIndicator: true,
          AssetSelect: true,
          RuiAutoComplete: true,
          SettingsItem: { template: '<div><slot /></div>' },
        },
      },
    });
  }

  function sourceSelect(): VueWrapper {
    return wrapper.findAllComponents({ name: 'RuiAutoComplete' })[0];
  }

  function ensSelect(): VueWrapper {
    return wrapper.findAllComponents({ name: 'RuiAutoComplete' })[1];
  }

  async function chooseEnsAvatars(): Promise<void> {
    sourceSelect().vm.$emit('update:modelValue', PurgeableImageCache.ENS_AVATARS);
    await nextTick();
  }

  async function purgeAndConfirm(): Promise<void> {
    await wrapper.find(BUTTON).trigger('click');
    await useConfirmStore().confirm();
    await flushPromises();
  }

  beforeEach(() => {
    vi.clearAllMocks();
    pinia = createCustomPinia();
    setActivePinia(pinia);
    spies.clearIconCache.mockResolvedValue(true);
    spies.clearEnsAvatarCache.mockResolvedValue(true);
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should purge nothing until the purge is confirmed', async () => {
    wrapper = createWrapper();

    await wrapper.find(BUTTON).trigger('click');
    await flushPromises();

    expect(useConfirmStore().visible).toBe(true);
    expect(spies.clearIconCache).not.toHaveBeenCalled();

    await useConfirmStore().dismiss();
    await flushPromises();

    expect(spies.clearIconCache).not.toHaveBeenCalled();
  });

  describe('asset icons', () => {
    it('should purge every asset icon when no asset is chosen', async () => {
      wrapper = createWrapper();

      await purgeAndConfirm();

      expect(spies.clearIconCache).toHaveBeenCalledExactlyOnceWith(null);
      expect(spies.setLastRefreshedAssetIcon).toHaveBeenCalledOnce();
    });

    it('should purge only the chosen asset icon, then clear the choice', async () => {
      wrapper = createWrapper();
      wrapper.findComponent(AssetSelect).vm.$emit('update:modelValue', 'ETH');
      await nextTick();

      await purgeAndConfirm();

      expect(spies.clearIconCache).toHaveBeenCalledExactlyOnceWith(['ETH']);
      expect(wrapper.findComponent(AssetSelect).props('modelValue')).toBe('');
    });

    it('should report the purge under the name of the source', async () => {
      wrapper = createWrapper();

      await purgeAndConfirm();

      expect(wrapper.findComponent(ActionStatusIndicator).props('status')).toEqual({
        error: '',
        success: 'data_management.purge_images_cache.success::data_management.purge_images_cache.label.asset_icons',
      });
    });
  });

  describe('ens avatars', () => {
    it('should offer the known ens names instead of an asset once chosen', async () => {
      wrapper = createWrapper();

      await chooseEnsAvatars();

      expect(wrapper.findComponent(AssetSelect).exists()).toBe(false);
      expect(ensSelect().props()).toMatchObject({ options: ['vitalik.eth', 'rotki.eth'] });
    });

    it('should purge every ens avatar when no name is chosen', async () => {
      wrapper = createWrapper();
      await chooseEnsAvatars();

      await purgeAndConfirm();

      expect(spies.clearEnsAvatarCache).toHaveBeenCalledExactlyOnceWith(null);
      expect(spies.refreshAvatarTimestamp).toHaveBeenCalledOnce();
      expect(spies.clearIconCache).not.toHaveBeenCalled();
    });

    it('should purge only the chosen ens avatars, then clear the choice', async () => {
      wrapper = createWrapper();
      await chooseEnsAvatars();
      ensSelect().vm.$emit('update:modelValue', ['rotki.eth']);
      await nextTick();

      await purgeAndConfirm();

      expect(spies.clearEnsAvatarCache).toHaveBeenCalledExactlyOnceWith(['rotki.eth']);
      expect(ensSelect().props()).toMatchObject({ modelValue: [] });
    });
  });
});
