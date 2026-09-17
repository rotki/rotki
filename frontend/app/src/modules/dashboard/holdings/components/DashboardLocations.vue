<script setup lang="ts">
import type { SourceKind } from '@/modules/dashboard/holdings/core/holdings-types';
import { Blockchain, toCapitalCase, toSentenceCase } from '@rotki/common';
import Eth2ValidatorLimitTooltip from '@/modules/accounts/blockchain/eth2/Eth2ValidatorLimitTooltip.vue';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { calculatePercentage } from '@/modules/core/common/data/calculation';
import { useLocations } from '@/modules/core/common/use-locations';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import LocationTile from '@/modules/dashboard/holdings/components/LocationTile.vue';
import { tileRoute } from '@/modules/dashboard/holdings/tile-route';
import { useDashboardHoldings } from '@/modules/dashboard/holdings/use-dashboard-holdings';
import { useLocationsStrip } from '@/modules/dashboard/holdings/use-locations-strip';
import { useSourceKindLabel } from '@/modules/dashboard/holdings/use-source-kind-label';
import { useNetWorthLoading } from '@/modules/dashboard/use-net-worth-loading';

const selectedKind = defineModel<SourceKind | undefined>('selectedKind');

const LOADING_TILES = 8;

const { t } = useI18n({ useScope: 'global' });

const grid = useTemplateRef<HTMLElement>('grid');
const modelExpanded = useSessionStorage<boolean>('rotki.dashboard.locations.expanded', false);

const { holdings } = useDashboardHoldings();
const isInitialLoading = useNetWorthLoading();
const { getBlockchainRedirectLink, getChainName } = useSupportedChains();
const { getLocationData } = useLocations();
const kindLabel = useSourceKindLabel();
const { width } = useElementSize(grid);

const { base, canExpand, hiddenCount, hiddenValue, visible } = useLocationsStrip({
  holdings,
  kind: selectedKind,
  modelExpanded,
  width,
});

const hasHoldings = computed<boolean>(() => get(holdings).length > 0);

function labelOf(location: string | undefined, chain: string | undefined): string {
  if (location)
    return getLocationData(location)?.name ?? toCapitalCase(location);
  return toSentenceCase(getChainName(chain ?? ''));
}
</script>

<template>
  <RuiCard
    v-if="isInitialLoading || hasHoldings"
    data-testid="dashboard-locations"
  >
    <div class="flex flex-wrap items-center justify-between gap-2 mb-3">
      <div class="flex items-center gap-2.5 text-h6">
        {{ t('dashboard.holdings.locations.title') }}
        <RuiChip
          v-if="selectedKind"
          size="sm"
          color="primary"
          closeable
          data-testid="dashboard-locations-kind"
          @click:close="selectedKind = undefined"
        >
          {{ kindLabel(selectedKind) }}
        </RuiChip>
      </div>
    </div>
    <div
      ref="grid"
      class="grid grid-cols-[repeat(auto-fill,minmax(210px,1fr))] gap-2"
    >
      <template v-if="isInitialLoading">
        <RuiSkeletonLoader
          v-for="tile in LOADING_TILES"
          :key="tile"
          class="h-14 rounded-md"
        />
      </template>
      <template v-else>
        <LocationTile
          v-for="holding in visible"
          :key="holding.place.key"
          :holding="holding"
          :label="labelOf(holding.place.location, holding.place.chain)"
          :to="tileRoute(holding.target, getBlockchainRedirectLink)"
          :share="calculatePercentage(holding.value, base)"
          :show-kinds="!selectedKind"
        >
          <template
            v-if="holding.place.chain === Blockchain.ETH2"
            #badge
          >
            <Eth2ValidatorLimitTooltip />
          </template>
        </LocationTile>
      </template>
    </div>
    <div
      v-if="!isInitialLoading && canExpand"
      class="flex justify-center mt-2"
    >
      <RuiButton
        variant="text"
        size="sm"
        data-testid="dashboard-locations-more"
        @click="modelExpanded = !modelExpanded"
      >
        <span
          v-if="hiddenCount > 0"
          class="inline-flex flex-wrap items-center justify-center gap-x-1.5"
        >
          <span class="text-rui-primary">{{ t('dashboard.holdings.locations.show_more', { count: hiddenCount }) }}</span>
          <span class="inline-flex items-center gap-1.5 text-rui-text-secondary before:content-['·']">
            <FiatDisplay :value="hiddenValue" />
          </span>
        </span>
        <span
          v-else
          class="text-rui-primary"
        >
          {{ t('dashboard.holdings.locations.show_less') }}
        </span>
      </RuiButton>
    </div>
  </RuiCard>
</template>
