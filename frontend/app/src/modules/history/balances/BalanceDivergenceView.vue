<script setup lang="ts">
import ChainSelect from '@/modules/accounts/blockchain/ChainSelect.vue';
import DivergenceBoundaryCard from '@/modules/history/balances/DivergenceBoundaryCard.vue';
import { useArchiveNodes } from '@/modules/history/balances/use-archive-nodes';
import { useBalanceDivergence } from '@/modules/history/balances/use-balance-divergence';
import { useDivergenceSelection } from '@/modules/history/balances/use-divergence-selection';
import HistoryEventNote from '@/modules/history/events/HistoryEventNote.vue';
import LocationLabelSelector from '@/modules/history/LocationLabelSelector.vue';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';
import InternalLink from '@/modules/shell/components/InternalLink.vue';

const { t } = useI18n({ useScope: 'global' });

const {
  chainOptions,
  locationLabelOptions,
  modelSelectedAsset,
  modelSelectedChain,
  modelSelectedLocationLabel,
  selectedEvmChain,
} = useDivergenceSelection();

const { boundaries, clear, error, find, loading, navigate, summary } = useBalanceDivergence();

const { hasArchiveNode, loading: archiveLoading } = useArchiveNodes(chainOptions);
const selectedChainHasArchive = hasArchiveNode(modelSelectedChain);

const missingArchiveNode = computed<boolean>(() =>
  !!get(modelSelectedChain) && !get(archiveLoading) && !get(selectedChainHasArchive),
);

const canFindDivergence = computed<boolean>(() =>
  !!get(modelSelectedAsset) && !!get(modelSelectedLocationLabel) && !!get(selectedEvmChain)
  && get(selectedChainHasArchive),
);

async function findDivergence(): Promise<void> {
  const asset = get(modelSelectedAsset);
  const evmChain = get(selectedEvmChain);
  const locationLabel = get(modelSelectedLocationLabel);
  if (!asset || !evmChain || !locationLabel)
    return;

  await find({ address: locationLabel, asset, evmChain });
}

watch([modelSelectedAsset, modelSelectedChain, modelSelectedLocationLabel], clear);
</script>

<template>
  <div class="h-full flex flex-col overflow-hidden">
    <div class="flex-1 overflow-y-auto p-4 md:p-6 flex flex-col gap-6">
      <div class="grid grid-cols-1 gap-4">
        <ChainSelect
          v-model="modelSelectedChain"
          :items="chainOptions"
          evm-only
          :label="t('balance_divergence.chain')"
          data-testid="balance-divergence-chain"
        />

        <LocationLabelSelector
          v-model="modelSelectedLocationLabel"
          :options="locationLabelOptions"
          :label="t('balance_divergence.location_label')"
          :disabled="locationLabelOptions.length === 0"
          data-testid="balance-divergence-location-label"
        />

        <AssetSelect
          v-model="modelSelectedAsset"
          variant="outlined"
          clearable
          :label="t('balance_divergence.asset')"
          :source="{ chain: modelSelectedChain, showIgnored: true }"
          data-testid="balance-divergence-asset"
        />
      </div>

      <div
        v-if="missingArchiveNode"
        class="text-sm text-rui-text-secondary"
        data-testid="balance-divergence-missing-archive"
      >
        <i18n-t
          keypath="balance_divergence.chain_missing_archive_node"
          tag="span"
          scope="global"
        >
          <template #chain>
            {{ modelSelectedChain }}
          </template>
          <template #link>
            <InternalLink :to="{ name: '/settings/rpc/' }">
              {{ t('balance_divergence.settings_link') }}
            </InternalLink>
          </template>
        </i18n-t>
      </div>

      <div
        v-if="chainOptions.length === 0 || locationLabelOptions.length === 0"
        class="text-sm text-rui-text-secondary"
      >
        {{ t('balance_divergence.no_options') }}
      </div>

      <div class="flex">
        <RuiButton
          color="primary"
          :loading="loading"
          :disabled="!canFindDivergence"
          data-testid="find-divergence"
          @click="findDivergence()"
        >
          <template #prepend>
            <RuiIcon
              name="lu-search"
              size="16"
            />
          </template>
          {{ t('balance_divergence.action') }}
        </RuiButton>
      </div>

      <div
        v-if="summary"
        class="text-sm text-rui-text-secondary"
      >
        {{ summary }}
      </div>

      <div
        v-if="boundaries.length > 0"
        class="flex flex-col gap-3"
        data-testid="divergence-boundaries"
      >
        <DivergenceBoundaryCard
          v-for="boundary in boundaries"
          :key="boundary.key"
          :boundary="boundary"
          :asset="modelSelectedAsset"
          :location="modelSelectedChain"
          @view="navigate(boundary.event, modelSelectedAsset ?? '')"
        />
      </div>

      <RuiAlert
        v-else-if="error"
        type="error"
        data-testid="divergence-error"
      >
        <HistoryEventNote
          :notes="error"
          :chain="modelSelectedChain"
          :asset="modelSelectedAsset"
        />
      </RuiAlert>
    </div>
  </div>
</template>
