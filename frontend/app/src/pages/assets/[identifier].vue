<script setup lang="ts">
import { type RawLocation } from 'vue-router';
import { type ComputedRef } from 'vue';
import { type AssetBalanceWithPrice } from '@rotki/common';
import { AssetAmountAndValueOverTime } from '@/premium/premium';
import { Routes } from '@/router/routes';

defineOptions({
  name: 'AssetBreakdown'
});

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
const isCustomAsset = computed(() => get(asset)?.isCustomAsset);

const { t } = useI18n();

const route = useRoute();

const isCollectionParent: ComputedRef<boolean> = computed(() => {
  const currentRoute = get(route);
  const collectionParent = currentRoute.query['collectionParent'];

  return !!collectionParent;
});

const editRoute = computed<RawLocation>(() => ({
  path: get(isCustomAsset)
    ? Routes.ASSET_MANAGER_CUSTOM
    : Routes.ASSET_MANAGER_MANAGED,
  query: {
    id: get(identifier)
  }
}));

const { balances } = useAggregatedBalances();
const collectionBalance: ComputedRef<AssetBalanceWithPrice[]> = computed(() => {
  if (!get(isCollectionParent)) {
    return [];
  }

  return (
    get(balances()).find(data => data.asset === get(identifier))?.breakdown ||
    []
  );
});
</script>

<template>
  <v-container class="pb-12">
    <v-row class="mt-12" align="center" justify="space-between">
      <v-col>
        <v-row align="center">
          <v-col cols="auto">
            <asset-icon
              :identifier="identifier"
              size="48px"
              :show-chain="!isCollectionParent"
            />
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
          <v-col v-if="!isCollectionParent" cols="auto">
            <v-btn icon :to="editRoute">
              <v-icon>mdi-pencil</v-icon>
            </v-btn>
          </v-col>
        </v-row>
      </v-col>
      <v-col v-if="!isCollectionParent" cols="auto">
        <v-row align="center">
          <v-col cols="auto">
            <div class="text-subtitle-2">{{ t('assets.ignore') }}</div>
          </v-col>
          <v-col>
            <v-switch :input-value="isIgnored" @change="toggleIgnoreAsset()" />
          </v-col>
        </v-row>
      </v-col>
    </v-row>
    <asset-value-row
      :is-collection-parent="isCollectionParent"
      class="mt-8"
      :identifier="identifier"
    />
    <asset-amount-and-value-over-time
      v-if="premium && !isCollectionParent"
      class="mt-8"
      :asset="identifier"
    />
    <asset-locations
      v-if="!isCollectionParent"
      class="mt-8"
      :identifier="identifier"
    />
    <card v-else class="mt-8" outlined-body>
      <template #title> {{ t('assets.multi_chain_assets') }} </template>
      <asset-balances :balances="collectionBalance" />
    </card>
  </v-container>
</template>
