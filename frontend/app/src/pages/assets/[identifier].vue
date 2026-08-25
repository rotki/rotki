<script setup lang="ts">
import { msg } from '@/message-key';
import ManagedAssetIgnoreSwitch from '@/modules/assets/admin/managed/ManagedAssetIgnoreSwitch.vue';
import AssetExternalLinks from '@/modules/assets/AssetExternalLinks.vue';
import AssetLocations from '@/modules/assets/AssetLocations.vue';
import AssetValueRow from '@/modules/assets/AssetValueRow.vue';
import AssetBalances from '@/modules/balances/AssetBalances.vue';
import { NoteLocation } from '@/modules/core/common/notes';
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
            :display-mode="contractInfo.location ? 'link' : 'copy'"
            hide-text
            size="18"
            class="[&_a]:!p-2.5"
          />

          <AssetExternalLinks
            v-if="asset"
            :coingecko="asset.coingecko"
            :cryptocompare="asset.cryptocompare"
          />
        </div>
      </div>
      <div class="flex items-center gap-2">
        <RuiButton
          v-if="!isCollectionParent"
          icon
          variant="text"
          data-testid="edit-asset"
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
        :breakdown="{ all: true, hide: true }"
      />
    </RuiCard>
  </TablePageLayout>
</template>
