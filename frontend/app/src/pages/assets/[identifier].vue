<script setup lang="ts">
import { msg } from '@/message-key';
import ManagedAssetIgnoreSwitch from '@/modules/assets/admin/managed/ManagedAssetIgnoreSwitch.vue';
import AssetExternalLinks from '@/modules/assets/AssetExternalLinks.vue';
import AssetLocations from '@/modules/assets/AssetLocations.vue';
import AssetValueRow from '@/modules/assets/AssetValueRow.vue';
import AssetBalances from '@/modules/balances/AssetBalances.vue';
import { NoteLocation } from '@/modules/core/common/notes';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { AssetAmountAndValueOverTime } from '@/modules/premium/premium';
import AssetIcon from '@/modules/shell/components/AssetIcon.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import AssetAmountAndValuePlaceholder from '@/modules/statistics/AssetAmountAndValuePlaceholder.vue';
import { useAssetDetail } from '@/pages/assets/use-asset-detail';

definePage({
  meta: {
    // label-only: gives the notes sidebar a title; not shown in the drawer or search.
    nav: { labelKey: msg.$t('common.assets'), icon: 'lu-coins', searchable: false },
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

const {
  asset,
  collectionAssetWithPrice,
  collectionBalance,
  collectionId,
  contractInfo,
  goToEdit,
  isCollectionParent,
  isCustomAsset,
  loadingIgnore,
  loadingSpam,
  loadingWhitelist,
  premium,
  toggleIgnoreAsset,
  toggleSpam,
  toggleWhitelistAsset,
} = useAssetDetail(() => identifier);

const { getChainName } = useSupportedChains();

const title = computed<string | undefined>(() => (get(isCustomAsset) ? get(asset)?.name : get(asset)?.symbol) ?? undefined);

const subtitle = computed<string | undefined>(() => (get(isCustomAsset) ? get(asset)?.customAssetType : get(asset)?.name) ?? undefined);

const chainName = computed<string | undefined>(() => {
  const location = get(contractInfo)?.location;
  return location ? getChainName(location) : undefined;
});
</script>

<template>
  <TablePageLayout
    class="p-4"
    hide-header
  >
    <div class="flex flex-wrap items-center justify-between w-full gap-4">
      <div class="flex items-center gap-4 min-w-0">
        <AssetIcon
          :identifier="identifier"
          size="48px"
          :show-chain="!isCollectionParent"
        />

        <div class="flex flex-col min-w-0">
          <span class="text-h5 leading-7 font-semibold truncate">{{ title }}</span>
          <div
            class="flex flex-wrap items-center gap-x-2 h-6 text-sm text-rui-text-secondary"
            data-testid="asset-meta"
          >
            <span v-if="subtitle">{{ subtitle }}</span>
            <template v-if="contractInfo">
              <span
                v-if="subtitle"
                class="size-1 rounded-full bg-rui-text-disabled"
              />
              <span v-if="chainName">{{ chainName }}</span>
              <HashLink
                :location="contractInfo.location"
                type="token"
                :text="contractInfo.address"
                :display-mode="contractInfo.location ? 'default' : 'copy'"
                size="14"
              />
            </template>
            <template v-if="asset?.coingecko || asset?.cryptocompare">
              <span class="size-1 rounded-full bg-rui-text-disabled" />
              <AssetExternalLinks
                :coingecko="asset.coingecko"
                :cryptocompare="asset.cryptocompare"
              />
            </template>
          </div>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <div
          v-if="!isCustomAsset"
          class="flex items-center gap-2"
        >
          <span class="text-sm">
            {{ t('assets.action.ignore') }}
          </span>
          <ManagedAssetIgnoreSwitch
            :asset="{ identifier, assetType: asset?.assetType, protocol: asset?.protocol }"
            :loading="loadingIgnore"
            :menu-loading="loadingWhitelist || loadingSpam"
            @toggle-ignore="toggleIgnoreAsset()"
            @toggle-whitelist="toggleWhitelistAsset()"
            @toggle-spam="toggleSpam()"
          />
        </div>
        <RuiButton
          v-if="!isCollectionParent"
          variant="outlined"
          color="primary"
          data-testid="edit-asset"
          @click="goToEdit()"
        >
          <template #prepend>
            <RuiIcon
              name="lu-pencil"
              size="16"
            />
          </template>
          {{ t('common.actions.edit') }}
        </RuiButton>
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

    <section
      v-else
      class="flex flex-col gap-3"
    >
      <h2 class="text-base font-semibold text-rui-text">
        {{ t('assets.multi_chain_assets') }}
      </h2>
      <TableFrame>
        <AssetBalances
          :balances="collectionBalance"
          :breakdown="{ all: true, hide: true }"
        />
      </TableFrame>
    </section>
  </TablePageLayout>
</template>
