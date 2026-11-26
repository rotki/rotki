<script setup lang="ts">
import { RuiButton, RuiIcon } from '@rotki/ui-library';
import { useI18n } from 'vue-i18n';
import { definePage } from 'vue-router/experimental';
import { msg } from '@/message-key';
import ManagedAssetIgnoreSwitch from '@/modules/assets/admin/managed/ManagedAssetIgnoreSwitch.vue';
import AssetDetailHeading from '@/modules/assets/AssetDetailHeading.vue';
import AssetLocations from '@/modules/assets/AssetLocations.vue';
import AssetValueRow from '@/modules/assets/AssetValueRow.vue';
import AssetBalances from '@/modules/balances/AssetBalances.vue';
import BalanceViewPicker from '@/modules/balances/components/BalanceViewPicker.vue';
import { provideHistoryView } from '@/modules/balances/view/balance-view';
import { useBalanceView } from '@/modules/balances/view/use-balance-view';
import { NoteLocation } from '@/modules/core/common/notes';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { AssetAmountAndValueOverTime } from '@/modules/premium/premium';
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

const { isHistory } = useBalanceView();
provideHistoryView(isHistory);

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
} = useAssetDetail(() => identifier, isHistory);
</script>

<template>
  <TablePageLayout
    class="p-4"
    hide-header
  >
    <div class="flex flex-wrap items-center justify-between w-full gap-4">
      <AssetDetailHeading
        :identifier="identifier"
        :asset="asset"
        :contract-info="contractInfo"
        :is-custom-asset="isCustomAsset"
        :is-collection-parent="isCollectionParent"
      />
      <div class="flex items-center gap-3">
        <BalanceViewPicker
          :asset="identifier"
          :is-collection-parent="isCollectionParent"
        />
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
