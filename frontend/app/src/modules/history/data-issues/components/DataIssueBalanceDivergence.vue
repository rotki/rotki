<script setup lang="ts">
import type { DivergenceBoundaryEvent } from '@/modules/history/balances/use-balance-divergence';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import DivergenceComparison from '@/modules/history/balances/DivergenceComparison.vue';
import DivergenceOutcome from '@/modules/history/balances/DivergenceOutcome.vue';
import { useDataIssueDivergence } from '@/modules/history/data-issues/use-data-issue-divergence';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import InternalLink from '@/modules/shell/components/InternalLink.vue';

const { issue, busy = false } = defineProps<{
  issue: DataIssue;
  busy?: boolean;
}>();

const emit = defineEmits<{
  navigate: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const {
  available,
  boundaries,
  canSearch,
  chain,
  chainName,
  checkingArchive,
  error,
  loading,
  missingArchive,
  search,
  status,
  summary,
  summaryInFooter,
  view,
} = useDataIssueDivergence(() => issue);

/** A diverged result has no line here: its search window carries that advice. */
const nextStep = computed<string | undefined>(() => {
  switch (get(status)) {
    case 'diverged_from_start':
      return t('data_issues.detail.divergence_from_start');
    case 'no_divergence':
      return t('data_issues.detail.divergence_no_mismatch');
    default:
      return undefined;
  }
});

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
    class="flex flex-col gap-2"
    data-testid="data-issue-balance-divergence"
  >
    <div class="flex items-center justify-between gap-2">
      <h3 class="inline-flex items-center gap-1 text-xs font-medium text-rui-text-secondary">
        {{ t('balance_divergence.title') }}
        <RuiTooltip
          :open-delay="200"
          :options="{ placement: 'top' }"
          class="inline-flex"
        >
          <template #activator>
            <RuiIcon
              name="lu-info"
              size="14"
            />
          </template>
          <i18n-t
            keypath="data_issues.detail.divergence_scope"
            tag="span"
            scope="global"
            data-testid="data-issue-divergence-scope"
          >
            <template #date>
              <DateDisplay
                :timestamp="issue.tsEnd"
                milliseconds
              />
            </template>
          </i18n-t>
        </RuiTooltip>
      </h3>
      <RuiButton
        color="primary"
        variant="outlined"
        size="sm"
        :disabled="busy || !canSearch"
        :loading="loading || checkingArchive"
        data-testid="data-issue-find-divergence"
        @click="search()"
      >
        <template #prepend>
          <RuiIcon
            name="lu-search"
            size="14"
          />
        </template>
        {{ status ? t('balance_divergence.search_again') : t('balance_divergence.action') }}
      </RuiButton>
    </div>
    <RuiAlert
      v-if="missingArchive"
      type="warning"
      data-testid="data-issue-divergence-missing-archive"
    >
      <i18n-t
        keypath="balance_divergence.chain_missing_archive_node"
        tag="span"
        scope="global"
      >
        <template #chain>
          {{ chainName }}
        </template>
        <template #link>
          <InternalLink :to="{ name: '/settings/rpc/' }">
            {{ t('balance_divergence.settings_link') }}
          </InternalLink>
        </template>
      </i18n-t>
    </RuiAlert>
    <DivergenceOutcome
      v-if="status"
      :status="status"
      :summary="summaryInFooter ? undefined : summary"
      :next-step="nextStep"
    />
    <DivergenceComparison
      v-if="boundaries.length > 0"
      :boundaries="boundaries"
      :asset="issue.asset ?? undefined"
      :location="chain"
      @view="viewBoundary($event)"
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
      data-testid="data-issue-divergence-error"
    />
  </section>
</template>
