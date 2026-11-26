<script setup lang="ts">
import type { IndexedBalanceSnapshot } from '@/modules/dashboard/snapshots/composables/use-snapshot-balance-rows';
import type { SnapshotWarning } from '@/modules/dashboard/snapshots/utils/snapshot-warnings';
import { RuiIcon, RuiTooltip } from '@rotki/ui-library';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import NftDetails from '@/modules/balances/nft/NftDetails.vue';

const { describeWarning, isNft, row, warnings } = defineProps<{
  row: IndexedBalanceSnapshot;
  /** The sanity warnings that caught this row; the flag shows only when there is one. */
  warnings?: SnapshotWarning[];
  /** Show the NFT's details instead of the asset's. */
  isNft: boolean;
  /** Turns a warning into the line the flag's tooltip lists. */
  describeWarning: (warning: SnapshotWarning) => string;
}>();
</script>

<template>
  <div class="flex items-center gap-2 min-w-0">
    <RuiTooltip
      v-if="warnings"
      :open-delay="200"
    >
      <template #activator>
        <RuiIcon
          name="lu-triangle-alert"
          size="18"
          class="text-rui-warning shrink-0"
          data-testid="snapshot-balances-flag"
        />
      </template>
      <ul class="list-disc pl-4">
        <li
          v-for="warning in warnings"
          :key="warning.code"
        >
          {{ describeWarning(warning) }}
        </li>
      </ul>
    </RuiTooltip>
    <AssetDetails
      v-if="!isNft"
      class="min-w-0 [&_.avatar]:ml-1.5 [&_.avatar]:mr-2"
      :asset="row.assetIdentifier"
      :actions="{ hideMenu: true }"
      :resolution="{ enableAssociation: false }"
    />
    <NftDetails
      v-else
      class="min-w-0"
      :identifier="row.assetIdentifier"
    />
  </div>
</template>
