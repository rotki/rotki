<template>
  <v-container class="pb-12">
    <v-row class="mt-12" align="center" justify="space-between">
      <v-col>
        <v-row align="center">
          <v-col cols="auto">
            <asset-icon :identifier="identifier" size="48px" />
          </v-col>
          <v-col v-if="!isCustomAsset" class="d-flex flex-column" cols="auto">
            <span class="text-h5 font-weight-medium">{{ symbol }}</span>
            <span class="text-subtitle-2 text--secondary">
              {{ name }}
            </span>
          </v-col>
          <v-col v-else class="d-flex flex-column" cols="auto">
            <span class="text-h5 font-weight-medium">{{ name }}</span>
            <span class="text-subtitle-2 text--secondary">
              {{ asset?.customAssetType }}
            </span>
          </v-col>
          <v-col cols="auto">
            <v-btn icon :to="editRoute">
              <v-icon>mdi-pencil</v-icon>
            </v-btn>
          </v-col>
        </v-row>
      </v-col>
      <v-col cols="auto">
        <v-row align="center">
          <v-col cols="auto">
            <div class="text-subtitle-2">{{ t('assets.ignore') }}</div>
          </v-col>
          <v-col>
            <v-switch :input-value="isIgnored" @change="toggleIgnoreAsset" />
          </v-col>
        </v-row>
      </v-col>
    </v-row>
    <asset-value-row class="mt-8" :identifier="identifier" />
    <asset-amount-and-value-over-time
      v-if="premium"
      class="mt-8"
      :asset="identifier"
    />
    <asset-locations class="mt-8" :identifier="identifier" />
  </v-container>
</template>

<script setup lang="ts">
import { RawLocation } from 'vue-router';
import AssetLocations from '@/components/assets/AssetLocations.vue';
import AssetValueRow from '@/components/assets/AssetValueRow.vue';
import { usePremium } from '@/composables/premium';
import { AssetAmountAndValueOverTime } from '@/premium/premium';
import { Routes } from '@/router/routes';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';

const props = defineProps({
  identifier: { required: true, type: String }
});

const { identifier } = toRefs(props);
const { isAssetIgnored, ignoreAsset, unignoreAsset } = useIgnoredAssetsStore();

const isIgnored = isAssetIgnored(identifier);

const toggleIgnoreAsset = async () => {
  const id = get(identifier);
  if (get(isIgnored)) {
    await unignoreAsset(id);
  } else {
    await ignoreAsset(id);
  }
};

const premium = usePremium();

const { assetName, assetSymbol, assetInfo } = useAssetInfoRetrieval();
const name = assetName(identifier);
const symbol = assetSymbol(identifier);
const asset = assetInfo(identifier);
const isCustomAsset = computed(() => get(assetInfo(identifier))?.isCustomAsset);

const { t } = useI18n();

const editRoute = computed<RawLocation>(() => ({
  path: get(isCustomAsset)
    ? Routes.ASSET_MANAGER_CUSTOM
    : Routes.ASSET_MANAGER_MANAGED,
  query: {
    id: get(identifier)
  }
}));
</script>
