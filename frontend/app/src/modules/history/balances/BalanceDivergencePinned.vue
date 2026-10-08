<script setup lang="ts">
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import BalanceDivergenceView from '@/modules/history/balances/BalanceDivergenceView.vue';
import DataIssueBalanceDivergence from '@/modules/history/data-issues/components/DataIssueBalanceDivergence.vue';
import HistoryEventAccount from '@/modules/history/events/HistoryEventAccount.vue';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import { PinnedNames } from '@/modules/session/types';
import { usePinnedPanel } from '@/modules/shell/pinned/use-pinned-panel';

const { issue } = defineProps<{
  issue?: DataIssue;
}>();

const { t } = useI18n({ useScope: 'global' });

const { pin } = usePinnedPanel(PinnedNames.BALANCE_DIVERGENCE);

function startNewSearch(): void {
  pin({});
}
</script>

<template>
  <div class="h-full flex flex-col overflow-hidden">
    <div
      v-if="issue"
      class="flex-1 overflow-y-auto p-4 md:p-6 flex flex-col gap-4"
      data-testid="balance-divergence-pinned-issue"
    >
      <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
        <LocationDisplay
          :identifier="issue.location"
          horizontal
          class="w-fit"
        />
        <HistoryEventAccount
          v-if="issue.locationLabel"
          :location="issue.location"
          :location-label="issue.locationLabel"
          data-testid="balance-divergence-pinned-account"
        />
        <AssetDetails
          v-if="issue.asset"
          :asset="issue.asset"
          data-testid="balance-divergence-pinned-asset"
        />
        <RuiButton
          class="ml-auto"
          variant="text"
          color="primary"
          size="sm"
          data-testid="balance-divergence-new-search"
          @click="startNewSearch()"
        >
          <template #prepend>
            <RuiIcon
              name="lu-search"
              size="14"
            />
          </template>
          {{ t('balance_divergence.new_search') }}
        </RuiButton>
      </div>
      <DataIssueBalanceDivergence
        :key="issue.id"
        :issue="issue"
      />
    </div>
    <BalanceDivergenceView v-else />
  </div>
</template>
