<script setup lang="ts">
import { type RawLocation } from 'vue-router';
import { type ComputedRef } from 'vue';
import { type AssetBalanceWithPrice } from '@rotki/common';
import { AssetAmountAndValueOverTime } from '@/premium/premium';
import { Routes } from '@/router/routes';

defineOptions({
  name: 'AssetBreakdown'
});

const props = defineProps<{
  identifier: string;
}>();

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

const { assetName, assetSymbol, assetInfo, tokenAddress } =
  useAssetInfoRetrieval();
const { getChain } = useSupportedChains();
const name = assetName(identifier);
const symbol = assetSymbol(identifier);
const asset = assetInfo(identifier);
const address = tokenAddress(identifier);
const chain = computed(() => {
  const evmChain = get(asset)?.evmChain;
  if (evmChain) {
    return getChain(evmChain);
  }
  return undefined;
});
const isCustomAsset = computed(() => get(asset)?.isCustomAsset);

const { t } = useI18n();

const route = useRoute();

const isCollectionParent: ComputedRef<boolean> = computed(() => {
  const currentRoute = get(route);
  const collectionParent = currentRoute.query['collectionParent'];

  return !!collectionParent;
});

const collectionId: ComputedRef<number | undefined> = computed(() => {
  if (!get(isCollectionParent)) {
    return undefined;
  }

  const collectionId = get(asset)?.collectionId;
  return (collectionId && parseInt(collectionId)) || undefined;
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
  <VContainer class="pb-12">
    <VRow class="mt-12" align="center" justify="space-between">
      <VCol>
        <VRow align="center">
          <VCol cols="auto">
            <AssetIcon
              :identifier="identifier"
              size="48px"
              :show-chain="!isCollectionParent"
            />
          </VCol>
          <VCol v-if="!isCustomAsset" class="flex flex-col" cols="auto">
            <span class="text-h5 font-medium">{{ symbol }}</span>
            <span class="text-subtitle-2 text--secondary">
              {{ name }}
            </span>
          </VCol>
          <VCol v-else class="flex flex-col" cols="auto">
            <span class="text-h5 font-medium">{{ name }}</span>
            <span class="text-subtitle-2 text--secondary">
              {{ asset?.customAssetType }}
            </span>
          </VCol>
          <VCol v-if="address" cols="auto">
            <HashLink
              :chain="chain"
              type="address"
              :text="address"
              link-only
              :show-icon="false"
            />
          </VCol>
          <VCol v-if="!isCollectionParent" cols="auto">
            <RuiButton icon variant="text" :to="editRoute">
              <VIcon>mdi-pencil</VIcon>
            </RuiButton>
          </VCol>
        </VRow>
      </VCol>
      <VCol v-if="!isCollectionParent" cols="auto">
        <VRow align="center">
          <VCol cols="auto">
            <div class="text-subtitle-2">{{ t('assets.ignore') }}</div>
          </VCol>
          <VCol>
            <VSwitch :input-value="isIgnored" @change="toggleIgnoreAsset()" />
          </VCol>
        </VRow>
      </VCol>
    </VRow>
    <AssetValueRow
      :is-collection-parent="isCollectionParent"
      class="mt-8"
      :identifier="identifier"
    />
    <AssetAmountAndValueOverTime
      v-if="premium"
      class="mt-8"
      :asset="identifier"
      :collection-id="collectionId"
    />
    <AssetLocations
      v-if="!isCollectionParent"
      class="mt-8"
      :identifier="identifier"
    />
    <Card v-else class="mt-8">
      <template #title> {{ t('assets.multi_chain_assets') }} </template>
      <AssetBalances :balances="collectionBalance" />
    </Card>
  </VContainer>
</template>
