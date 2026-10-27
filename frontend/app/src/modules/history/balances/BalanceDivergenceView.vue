<script setup lang="ts">
import ChainSelect from '@/modules/accounts/blockchain/ChainSelect.vue';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import DivergenceComparison from '@/modules/history/balances/DivergenceComparison.vue';
import DivergenceOutcome from '@/modules/history/balances/DivergenceOutcome.vue';
import { useArchiveNodes } from '@/modules/history/balances/use-archive-nodes';
import { useBalanceDivergence } from '@/modules/history/balances/use-balance-divergence';
import { useDivergenceSelection } from '@/modules/history/balances/use-divergence-selection';
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

const { boundaries, clear, error, find, loading, navigate, result, summary, summaryInFooter } = useBalanceDivergence();
const { getChainName } = useSupportedChains();

const { hasArchiveNode, loading: archiveLoading } = useArchiveNodes(chainOptions);
const selectedChainHasArchive = hasArchiveNode(modelSelectedChain);

const selectedChainName = computed<string>(() => {
  const chain = get(modelSelectedChain);
  return chain ? getChainName(chain) : '';
});

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
          clearable
          :label="t('balance_divergence.asset')"
          :source="{ chain: modelSelectedChain, showIgnored: true }"
          data-testid="balance-divergence-asset"
        />
      </div>

      <RuiAlert
        v-if="missingArchiveNode"
        type="warning"
        data-testid="balance-divergence-missing-archive"
      >
        <i18n-t
          keypath="balance_divergence.chain_missing_archive_node"
          tag="span"
          scope="global"
        >
          <template #chain>
            {{ selectedChainName }}
          </template>
          <template #link>
            <InternalLink :to="{ name: '/settings/rpc/' }">
              {{ t('balance_divergence.settings_link') }}
            </InternalLink>
          </template>
        </i18n-t>
      </RuiAlert>

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

      <DivergenceOutcome
        v-if="result"
        :status="result.status"
        :summary="summaryInFooter ? undefined : summary"
      />

      <DivergenceComparison
        v-if="boundaries.length > 0"
        :boundaries="boundaries"
        :asset="modelSelectedAsset"
        :location="modelSelectedChain"
        @view="navigate($event.event, modelSelectedAsset ?? '')"
      >
        <template
          v-if="summary && summaryInFooter"
          #footer
        >
          {{ summary }}
        </template>
      </DivergenceComparison>

      <RuiAlert
        v-if="error"
        type="error"
        :description="t('balance_divergence.search_failed')"
        data-testid="divergence-error"
      />
    </div>
  </div>
</template>
