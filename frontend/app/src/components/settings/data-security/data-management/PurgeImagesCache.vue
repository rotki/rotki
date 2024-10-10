<script setup lang="ts">
import { PurgeableImageCache } from '@/types/session/purge';

const { t } = useI18n();

const purgable = [
  {
    id: PurgeableImageCache.ASSET_ICONS,
    text: t('data_management.purge_images_cache.label.asset_icons'),
  },
  {
    id: PurgeableImageCache.ENS_AVATARS,
    text: t('data_management.purge_images_cache.label.ens_avatars'),
  },
];

const source = ref<PurgeableImageCache>(PurgeableImageCache.ASSET_ICONS);

const assetToClear = ref<string>('');
const ensToClear = ref<string[]>([]);

const { ensNames } = storeToRefs(useAddressesNamesStore());

const ensNamesList = computed<string[]>(
  () => Object.values(get(ensNames)).filter(value => !!value) as string[],
);

const { clearIconCache } = useAssetIconApi();
const { setLastRefreshedAssetIcon } = useAssetIconStore();
const { clearEnsAvatarCache } = useAddressesNamesApi();
const { setLastRefreshedAvatar } = useAddressesNamesStore();

async function purgeSource(source: PurgeableImageCache) {
  if (source === PurgeableImageCache.ASSET_ICONS) {
    const asset = get(assetToClear);
    await clearIconCache(asset ? [asset] : null);
    setLastRefreshedAssetIcon();
    set(assetToClear, '');
  }
  else {
    const ens = get(ensToClear);
    await clearEnsAvatarCache(ens.length > 0 ? ens : null);
    setLastRefreshedAvatar();
    set(ensToClear, []);
  }
}

const { status, pending, showConfirmation } = useCacheClear<PurgeableImageCache>(
  purgable,
  purgeSource,
  (source: string) => ({
    success: t('data_management.purge_images_cache.success', {
      source,
    }),
    error: t('data_management.purge_images_cache.error', {
      source,
    }),
  }),
  (source: string) => ({
    title: t('data_management.purge_images_cache.confirm.title'),
    message: t('data_management.purge_images_cache.confirm.message', {
      source,
    }),
  }),
);
</script>

<template>
  <SettingsItem>
    <template #title>
      {{ t('data_management.purge_images_cache.title') }}
    </template>
    <template #subtitle>
      {{ t('data_management.purge_images_cache.subtitle') }}
    </template>
    <div class="flex flex-col gap-4">
      <RuiAutoComplete
        v-model="source"
        variant="outlined"
        :label="t('data_management.purge_images_cache.select_image_source')"
        :options="purgable"
        text-attr="text"
        key-attr="id"
        hide-details
        :disabled="pending"
      />
      <AssetSelect
        v-if="source === PurgeableImageCache.ASSET_ICONS"
        v-model="assetToClear"
        outlined
        :label="t('data_management.purge_images_cache.label.asset_to_clear')"
        :hint="t('data_management.purge_images_cache.hint')"
      />
      <RuiAutoComplete
        v-else
        v-model="ensToClear"
        :options="ensNamesList"
        variant="outlined"
        chips
        clearable
        custom-value
        :label="t('data_management.purge_images_cache.label.ens_to_clear')"
        :hint="t('data_management.purge_images_cache.hint')"
      />
    </div>

    <ActionStatusIndicator
      v-if="status"
      :status="status"
    />

    <div class="flex justify-end">
      <RuiButton
        :disabled="!source || pending"
        :loading="pending"
        color="error"
        @click="showConfirmation(source)"
      >
        <div class="flex items-center gap-2">
          <RuiIcon
            name="delete-bin-line"
            size="16"
          />
          <span> {{ t('purge_selector.tooltip') }} </span>
        </div>
      </RuiButton>
    </div>
  </SettingsItem>
</template>
