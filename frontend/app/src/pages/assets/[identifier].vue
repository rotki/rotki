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
const router = useRouter();

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

const goToEdit = () => {
  router.push(get(editRoute));
};
</script>

<template>
  <TablePageLayout class="p-4" hide-header>
    <div class="flex flex-wrap justify-between w-full">
      <div class="flex gap-4 items-center">
        <AssetIcon
          :identifier="identifier"
          size="48px"
          :show-chain="!isCollectionParent"
        />

        <div v-if="!isCustomAsset" class="flex flex-col">
          <span class="text-h5 font-medium">{{ symbol }}</span>
          <span class="text-body-2 text-rui-text-secondary">
            {{ name }}
          </span>
        </div>

        <div v-else class="flex flex-col">
          <span class="text-h5 font-medium">{{ name }}</span>
          <span class="text-body-2 text-rui-text-secondary">
            {{ asset?.customAssetType }}
          </span>
        </div>

        <HashLink
          v-if="address"
          :chain="chain"
          type="address"
          :text="address"
          link-only
          size="18"
          :show-icon="false"
        />

        <RuiButton
          v-if="!isCollectionParent"
          icon
          variant="text"
          @click="goToEdit()"
        >
          <RuiIcon name="pencil-line" />
        </RuiButton>
      </div>
      <div class="flex gap-4 items-center">
        <div class="text-body-2">
          {{ t('assets.ignore') }}
        </div>

        <VSwitch :input-value="isIgnored" @change="toggleIgnoreAsset()" />
      </div>
    </div>

    <AssetValueRow
      :is-collection-parent="isCollectionParent"
      :identifier="identifier"
    />

    <AssetAmountAndValueOverTime
      v-if="premium"
      :asset="identifier"
      :collection-id="collectionId"
    />

    <AssetLocations v-if="!isCollectionParent" :identifier="identifier" />

    <RuiCard v-else>
      <template #header>
        {{ t('assets.multi_chain_assets') }}
      </template>

      <AssetBalances :balances="collectionBalance" />
    </RuiCard>
  </TablePageLayout>
</template>
