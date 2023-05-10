<script setup lang="ts">
import { type ComputedRef, type Ref } from 'vue';
import { OtherPurge } from '@/types/session/purge';

const { tc } = useI18n();

const purgable = [
  {
    id: OtherPurge.ASSET_ICONS,
    text: tc('data_management.purge_images_cache.label.asset_icons')
  },
  {
    id: OtherPurge.ENS_AVATARS,
    text: tc('data_management.purge_images_cache.label.ens_avatars')
  }
];

const source: Ref<OtherPurge> = ref(OtherPurge.ASSET_ICONS);

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

const purgeSource = async (source: OtherPurge) => {
  if (source === OtherPurge.ASSET_ICONS) {
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

const { status, pending, showConfirmation } = useCacheRefresh(
  purgable,
  purgeSource,
  (source: string) => ({
    success: tc('data_management.purge_images_cache.success', 0, {
      source
    }),
    error: tc('data_management.purge_images_cache.error', 0, {
      source
    })
  }),
  (source: string) => ({
    title: tc('data_management.purge_images_cache.confirm.title'),
    message: tc('data_management.purge_images_cache.confirm.message', 0, {
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
        {{ tc('data_management.purge_images_cache.title') }}
      </div>
      <div>
        {{ tc('data_management.purge_images_cache.subtitle') }}
      </div>
    </div>

    <v-row class="mb-0" align="center">
      <v-col cols="12" :md="true" class="mb-n7 mb-md-0">
        <v-autocomplete
          v-model="source"
          outlined
          :label="tc('data_management.purge_images_cache.select_image_source')"
          :items="purgable"
          item-text="text"
          item-value="id"
          :disabled="pending"
        />
      </v-col>
      <v-col md="6">
        <asset-select
          v-if="source === OtherPurge.ASSET_ICONS"
          v-model="assetToClear"
          outlined
          persistent-hint
          :label="tc('data_management.purge_images_cache.label.asset_to_clear')"
          :hint="tc('data_management.purge_images_cache.hint')"
        />
        <v-combobox
          v-else
          v-model="ensToClear"
          :items="ensNamesList"
          outlined
          :class="css['ens-input']"
          chips
          deletable-chips
          clearable
          :label="tc('data_management.purge_images_cache.label.ens_to_clear')"
          :hint="tc('data_management.purge_images_cache.hint')"
          multiple
          persistent-hint
        />
      </v-col>

      <v-col cols="auto">
        <v-tooltip open-delay="400" top>
          <template #activator="{ on, attrs }">
            <v-btn
              class="mt-n8"
              v-bind="attrs"
              icon
              :disabled="!source || pending"
              :loading="pending"
              v-on="on"
              @click="showConfirmation(source)"
            >
              <v-icon>mdi-delete</v-icon>
            </v-btn>
          </template>
          <span> {{ tc('data_management.purge_images_cache.tooltip') }} </span>
        </v-tooltip>
      </v-col>
    </v-row>

    <action-status-indicator v-if="status" :status="status" />
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
