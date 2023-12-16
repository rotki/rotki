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
  <div>
    <RuiCardHeader class="p-0 mb-4">
      <template #header>
        {{ t('data_management.purge_images_cache.title') }}
      </template>
      <template #subheader>
        {{ t('data_management.purge_images_cache.subtitle') }}
      </template>
    </RuiCardHeader>

    <div class="flex items-center gap-4">
      <div class="flex flex-col md:flex-row md:gap-4 flex-1">
        <RuiAutoComplete
          v-model="source"
          class="flex-1"
          variant="outlined"
          :label="t('data_management.purge_images_cache.select_image_source')"
          :options="purgable"
          text-attr="text"
          key-attr="id"
          :disabled="pending"
        />
        <AssetSelect
          v-if="source === PurgeableImageCache.ASSET_ICONS"
          v-model="assetToClear"
          class="flex-1"
          outlined
          :label="t('data_management.purge_images_cache.label.asset_to_clear')"
          :hint="t('data_management.purge_images_cache.hint')"
        />
        <RuiAutoComplete
          v-else
          v-model="ensToClear"
          class="flex-1"
          :options="ensNamesList"
          variant="outlined"
          chips
          clearable
          custom-value
          :label="t('data_management.purge_images_cache.label.ens_to_clear')"
          :hint="t('data_management.purge_images_cache.hint')"
        />
      </div>

      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
        class="-mt-6"
      >
        <template #activator>
          <RuiButton
            variant="text"
            icon
            :disabled="!source || pending"
            :loading="pending"
            @click="showConfirmation(source)"
          >
            <RuiIcon name="delete-bin-line" />
          </RuiButton>
        </template>
        <span> {{ t('data_management.purge_images_cache.tooltip') }} </span>
      </RuiTooltip>
    </div>

    <ActionStatusIndicator
      v-if="status"
      class="mt-4"
      :status="status"
    />
  </div>
</template>
