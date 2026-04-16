<script setup lang="ts">
import type { AssetBalanceWithPrice } from '@rotki/common';
import { externalLinks } from '@shared/external-links';
import ManagedAssetIgnoreSwitch from '@/modules/assets/admin/managed/ManagedAssetIgnoreSwitch.vue';
import AssetLocations from '@/modules/assets/AssetLocations.vue';
import AssetValueRow from '@/modules/assets/AssetValueRow.vue';
import { type AssetResolutionOptions, useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import AssetBalances from '@/modules/balances/AssetBalances.vue';
import { useAggregatedBalances } from '@/modules/balances/use-aggregated-balances';
import { getPublicServiceImagePath } from '@/modules/core/common/file/file';
import { NoteLocation } from '@/modules/core/common/notes';
import { AssetAmountAndValueOverTime } from '@/modules/premium/premium';
import { usePremium } from '@/modules/premium/use-premium';
import AppImage from '@/modules/shell/components/AppImage.vue';
import AssetIcon from '@/modules/shell/components/AssetIcon.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import AssetAmountAndValuePlaceholder from '@/modules/statistics/AssetAmountAndValuePlaceholder.vue';
import { useAssetPageActions } from '@/pages/assets/use-asset-page-actions';

definePage({
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.ASSETS,
  },
  props: true,
});

defineOptions({
  name: 'AssetBreakdown',
});

const { identifier } = defineProps<{
  identifier: string;
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const route = useRoute();

const { coingeckoAsset, cryptocompareAsset } = externalLinks;

const { refetchAssetInfo, useAssetContractInfo, useAssetInfo } = useAssetInfoRetrieval();
const premium = usePremium();
const { useBalances } = useAggregatedBalances();

const aggregatedBalances = useBalances();

const isCollectionParent = computed<boolean>(() => {
  const currentRoute = get(route);
  const collectionParent = currentRoute.query.collectionParent;

  return !!collectionParent;
});

const assetRetrievalOption = computed<AssetResolutionOptions>(() => ({
  collectionParent: get(isCollectionParent),
}));

const asset = useAssetInfo(() => identifier, assetRetrievalOption);
const contractInfo = useAssetContractInfo(() => identifier, assetRetrievalOption);

const {
  loadingIgnore,
  loadingSpam,
  loadingWhitelist,
  toggleIgnoreAsset,
  toggleSpam,
  toggleWhitelistAsset,
} = useAssetPageActions({
  asset,
  identifier: computed<string>(() => identifier),
  refetchAssetInfo,
});

const isCustomAsset = computed(() => get(asset)?.isCustomAsset);

const collectionId = computed<number | undefined>(() => {
  if (!get(isCollectionParent))
    return undefined;

  const collectionId = get(asset)?.collectionId;
  return (collectionId && parseInt(collectionId)) || undefined;
});

const editRoute = computed(() => ({
  path: get(isCustomAsset) ? '/asset-manager/custom' : '/asset-manager/managed',
  query: {
    id: identifier,
  },
}));

const collectionBalance = computed<AssetBalanceWithPrice[]>(() => {
  if (!get(isCollectionParent))
    return [];

  return get(aggregatedBalances).find(data => data.asset === identifier)?.breakdown || [];
});

const collectionAssetWithPrice = computed<string | undefined>(() => {
  const collectionBalanceVal = get(collectionBalance);

  const id = identifier;

  if (collectionBalanceVal.length === 0) {
    return id;
  }

  if (collectionBalanceVal.some(item => item.asset === id)) {
    return id;
  }

  return collectionBalanceVal[0].asset;
});

function goToEdit(): void {
  router.push(get(editRoute));
}
</script>

<template>
  <TablePageLayout
    class="p-4"
    hide-header
  >
    <div class="flex flex-wrap justify-between w-full gap-4">
      <div class="flex gap-4 items-center">
        <AssetIcon
          :identifier="identifier"
          size="48px"
          :show-chain="!isCollectionParent"
        />

        <div
          v-if="!isCustomAsset"
          class="flex flex-col"
        >
          <span class="text-h5 font-medium">{{ asset?.symbol }}</span>
          <span class="text-body-2 text-rui-text-secondary">
            {{ asset?.name }}
          </span>
        </div>

        <div
          v-else
          class="flex flex-col"
        >
          <span class="text-h5 font-medium">{{ asset?.name }}</span>
          <span class="text-body-2 text-rui-text-secondary">
            {{ asset?.customAssetType }}
          </span>
        </div>

        <div class="flex items-center gap-2 ml-4">
          <HashLink
            v-if="contractInfo"
            :location="contractInfo.location"
            type="token"
            :text="contractInfo.address"
            display-mode="link"
            hide-text
            size="18"
            class="[&_a]:!p-2.5"
          />

          <template v-if="asset">
            <ExternalLink
              v-if="asset.coingecko"
              custom
              :url="coingeckoAsset.replace('$symbol', asset.coingecko)"
            >
              <RuiButton
                size="sm"
                icon
              >
                <template #prepend>
                  <AppImage
                    size="30px"
                    :src="getPublicServiceImagePath('coingecko.svg')"
                  />
                </template>
              </RuiButton>
            </ExternalLink>
            <ExternalLink
              v-if="asset.cryptocompare"
              custom
              :url="cryptocompareAsset.replace('$symbol', asset.cryptocompare)"
            >
              <RuiButton
                size="sm"
                icon
              >
                <template #prepend>
                  <AppImage
                    size="30px"
                    :src="getPublicServiceImagePath('cryptocompare.svg')"
                  />
                </template>
              </RuiButton>
            </ExternalLink>
          </template>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <RuiButton
          v-if="!isCollectionParent"
          icon
          variant="text"
          @click="goToEdit()"
        >
          <RuiIcon name="lu-pencil" />
        </RuiButton>

        <template v-if="!isCustomAsset">
          <div class="text-body-2 mr-4">
            {{ t('assets.action.ignore') }}
          </div>

          <ManagedAssetIgnoreSwitch
            :asset="{ identifier, assetType: asset?.assetType, protocol: asset?.protocol }"
            :loading="loadingIgnore"
            :menu-loading="loadingWhitelist || loadingSpam"
            @toggle-ignore="toggleIgnoreAsset()"
            @toggle-whitelist="toggleWhitelistAsset()"
            @toggle-spam="toggleSpam()"
          />
        </template>
      </div>
    </div>

    <AssetValueRow
      :is-collection-parent="isCollectionParent"
      :identifier="identifier"
    />

    <AssetAmountAndValueOverTime
      v-if="premium"
      :asset="identifier"
      :price-asset="collectionAssetWithPrice"
      :collection-id="collectionId"
    />

    <AssetAmountAndValuePlaceholder v-else />

    <AssetLocations
      v-if="!isCollectionParent"
      :identifier="identifier"
    />

    <RuiCard v-else>
      <template #header>
        {{ t('assets.multi_chain_assets') }}
      </template>

      <AssetBalances
        :balances="collectionBalance"
        all-breakdown
        hide-breakdown
      />
    </RuiCard>
  </TablePageLayout>
</template>
