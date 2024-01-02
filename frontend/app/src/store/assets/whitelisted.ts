import { type MaybeRef } from '@vueuse/core';
import { type ActionStatus } from '@/types/action';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';

export const useWhitelistedAssetsStore = defineStore(
  'assets/whitelisted',
  () => {
    const whitelistedAssets: Ref<string[]> = ref([]);
    const { notify } = useNotificationsStore();
    const { t } = useI18n();

    const {
      getWhitelistedAssets,
      addAssetToWhitelist,
      removeAssetFromWhitelist
    } = useAssetWhitelistApi();

    const { fetchIgnoredAssets } = useIgnoredAssetsStore();

    const fetchWhitelistedAssets = async (): Promise<void> => {
      try {
        const whitelisted = await getWhitelistedAssets();
        set(whitelistedAssets, whitelisted);
      } catch (e: any) {
        const title = t('actions.session.whitelisted_assets.error.title');
        const message = t('actions.session.whitelisted_assets.error.message', {
          error: e.message
        });
        notify({
          title,
          message,
          display: true
        });
      }
    };

    const whitelistAsset = async (token: string): Promise<ActionStatus> => {
      try {
        await addAssetToWhitelist(token);
        await fetchWhitelistedAssets();
        await fetchIgnoredAssets();
        return { success: true };
      } catch (e: any) {
        notify({
          title: t('ignore.whitelist.failed.whitelist_title').toString(),
          message: t('ignore.whitelist.failed.whitelist_message', {
            message: e.message
          }).toString(),
          display: true
        });
        return { success: false, message: e.message };
      }
    };

    const unWhitelistAsset = async (token: string): Promise<ActionStatus> => {
      try {
        await removeAssetFromWhitelist(token);
        await fetchWhitelistedAssets();
        await fetchIgnoredAssets();
        return { success: true };
      } catch (e: any) {
        notify({
          title: t('ignore.whitelist.failed.unwhitelist_title').toString(),
          message: t('ignore.whitelist.failed.unwhitelist_message', {
            message: e.message
          }).toString(),
          display: true
        });
        return { success: false, message: e.message };
      }
    };

    const isAssetWhitelisted = (asset: MaybeRef<string>) =>
      computed<boolean>(() => {
        const selectedAsset = get(asset);
        return get(whitelistedAssets).includes(selectedAsset);
      });

    return {
      whitelistedAssets,
      fetchWhitelistedAssets,
      whitelistAsset,
      unWhitelistAsset,
      isAssetWhitelisted
    };
  }
);
