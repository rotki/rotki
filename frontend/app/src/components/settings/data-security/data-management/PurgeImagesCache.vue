<script setup lang="ts">
import { type ComputedRef, type Ref } from 'vue';
import { PurgeableImageCache } from '@/types/session/purge';

const { t } = useI18n();

const purgable = [
  {
    id: PurgeableImageCache.ASSET_ICONS,
    text: t('data_management.purge_images_cache.label.asset_icons')
  },
  {
    id: PurgeableImageCache.ENS_AVATARS,
    text: t('data_management.purge_images_cache.label.ens_avatars')
  }
];

const source: Ref<PurgeableImageCache> = ref(PurgeableImageCache.ASSET_ICONS);

const assetToClear: Ref<string> = ref('');
const ensToClear: Ref<string[]> = ref([]);

const { ensNames } = storeToRefs(useAddressesNamesStore());

const ensNamesList: ComputedRef<string[]> = computed(
  () => Object.values(get(ensNames)).filter(value => !!value) as string[]
);

const { clearIconCache } = useAssetIconApi();
const { setLastRefreshedAssetIcon } = useAssetIcon();
const { clearEnsAvatarCache } = useAddressesNamesApi();
const { setLastRefreshedAvatar } = useAddressesNamesStore();

const purgeSource = async (source: PurgeableImageCache) => {
  if (source === PurgeableImageCache.ASSET_ICONS) {
    const asset = get(assetToClear);
    await clearIconCache(asset ? [asset] : null);
    setLastRefreshedAssetIcon();
    set(assetToClear, '');
  } else {
    const ens = get(ensToClear);
    await clearEnsAvatarCache(ens.length > 0 ? ens : null);
    setLastRefreshedAvatar();
    set(ensToClear, []);
  }
};

const { status, pending, showConfirmation } =
  useCacheClear<PurgeableImageCache>(
    purgable,
    purgeSource,
    (source: string) => ({
      success: t('data_management.purge_images_cache.success', {
        source
      }),
      error: t('data_management.purge_images_cache.error', {
        source
      })
    }),
    (source: string) => ({
      title: t('data_management.purge_images_cache.confirm.title'),
      message: t('data_management.purge_images_cache.confirm.message', {
        source
      })
    })
  );

const css = useCssModule();
</script>

<template>
  <div>
    <div class="mb-6">
      <div class="text-h6">
        {{ t('data_management.purge_images_cache.title') }}
      </div>
      <div>
        {{ t('data_management.purge_images_cache.subtitle') }}
      </div>
    </div>

    <VRow class="mb-0" align="center">
      <VCol cols="12" :md="true" class="mb-n7 mb-md-0">
        <VAutocomplete
          v-model="source"
          outlined
          :label="t('data_management.purge_images_cache.select_image_source')"
          :items="purgable"
          item-text="text"
          item-value="id"
          :disabled="pending"
        />
      </VCol>
      <VCol md="6">
        <AssetSelect
          v-if="source === PurgeableImageCache.ASSET_ICONS"
          v-model="assetToClear"
          outlined
          persistent-hint
          :label="t('data_management.purge_images_cache.label.asset_to_clear')"
          :hint="t('data_management.purge_images_cache.hint')"
        />
        <VCombobox
          v-else
          v-model="ensToClear"
          :items="ensNamesList"
          outlined
          :class="css['ens-input']"
          chips
          deletable-chips
          clearable
          :label="t('data_management.purge_images_cache.label.ens_to_clear')"
          :hint="t('data_management.purge_images_cache.hint')"
          multiple
          persistent-hint
        />
      </VCol>

      <VCol cols="auto">
        <VTooltip open-delay="400" top>
          <template #activator="{ on, attrs }">
            <RuiButton
              class="mt-n8"
              v-bind="attrs"
              icon
              variant="text"
              :disabled="!source || pending"
              :loading="pending"
              v-on="on"
              @click="showConfirmation(source)"
            >
              <VIcon>mdi-delete</VIcon>
            </RuiButton>
          </template>
          <span> {{ t('data_management.purge_images_cache.tooltip') }} </span>
        </VTooltip>
      </VCol>
    </VRow>

    <ActionStatusIndicator v-if="status" :status="status" />
  </div>
</template>

<style module lang="scss">
.ens-input {
  :global {
    .v-select {
      &__selections {
        min-height: auto !important;
      }
    }
  }
}
</style>
