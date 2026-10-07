<script setup lang="ts">
import type { HistoricalBalanceDivergenceResponse } from '@/modules/history/balances/types';
import type { DivergenceBoundaryEvent } from '@/modules/history/balances/use-balance-divergence';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import DivergenceBoundaryCard from '@/modules/history/balances/DivergenceBoundaryCard.vue';
import { useDataIssueDivergence } from '@/modules/history/data-issues/use-data-issue-divergence';
import HistoryEventNote from '@/modules/history/events/HistoryEventNote.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import InternalLink from '@/modules/shell/components/InternalLink.vue';

const { issue, busy = false, initialResult } = defineProps<{
  issue: DataIssue;
  busy?: boolean;
  initialResult?: HistoricalBalanceDivergenceResponse;
}>();

const emit = defineEmits<{
  navigate: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const { available, boundaries, canSearch, chain, error, loading, missingArchive, search, summary, view }
  = useDataIssueDivergence(() => issue, () => initialResult);

function viewBoundary(boundary: DivergenceBoundaryEvent): void {
  if (!boundary.event.groupIdentifier)
    return;
  view(boundary);
  emit('navigate');
}
</script>

<template>
  <section
    v-if="available"
    class="flex flex-col gap-3"
    data-testid="data-issue-balance-divergence"
  >
    <div class="text-overline text-rui-text-secondary">
      {{ t('balance_divergence.title') }}
    </div>
    <div class="text-body-2">
      {{ t('data_issues.detail.divergence_until') }}
      <DateDisplay
        :timestamp="issue.tsEnd"
        milliseconds
      />
    </div>
    <p class="text-body-2 text-rui-text-secondary">
      {{ t('data_issues.detail.divergence_hint') }}
    </p>
    <div
      v-if="missingArchive"
      class="text-body-2 text-rui-text-secondary"
      data-testid="data-issue-divergence-missing-archive"
    >
      <i18n-t
        keypath="balance_divergence.chain_missing_archive_node"
        tag="span"
        scope="global"
      >
        <template #chain>
          {{ chain }}
        </template>
        <template #link>
          <InternalLink :to="{ name: '/settings/rpc/' }">
            {{ t('balance_divergence.settings_link') }}
          </InternalLink>
        </template>
      </i18n-t>
    </div>
    <RuiButton
      class="self-start"
      color="primary"
      variant="outlined"
      :disabled="busy || !canSearch"
      :loading="loading"
      data-testid="data-issue-find-divergence"
      @click="search()"
    >
      <template #prepend>
        <RuiIcon
          name="lu-search"
          size="16"
        />
      </template>
      {{ t('balance_divergence.action') }}
    </RuiButton>
    <p
      v-if="summary"
      class="text-body-2 text-rui-text-secondary"
      data-testid="data-issue-divergence-summary"
    >
      {{ summary }}
    </p>
    <DivergenceBoundaryCard
      v-for="boundary in boundaries"
      :key="boundary.key"
      :boundary="boundary"
      :asset="issue.asset ?? undefined"
      :location="chain"
      @view="viewBoundary(boundary)"
    />
    <RuiAlert
      v-if="error"
      type="error"
      data-testid="data-issue-divergence-error"
    >
      <HistoryEventNote
        :notes="error"
        :chain="chain"
        :context="{ asset: issue.asset ?? undefined }"
      />
    </RuiAlert>
  </section>
</template>
