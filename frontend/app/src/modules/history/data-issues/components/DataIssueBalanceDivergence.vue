<script setup lang="ts">
import type { DivergenceBoundaryEvent } from '@/modules/history/balances/use-balance-divergence';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import DivergenceBoundaryCard from '@/modules/history/balances/DivergenceBoundaryCard.vue';
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
  view,
} = useDataIssueDivergence(() => issue);

const nextStep = computed<string | undefined>(() => {
  switch (get(status)) {
    case 'diverged':
      return t('data_issues.detail.divergence_next_step');
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
    class="flex flex-col gap-3"
    data-testid="data-issue-balance-divergence"
  >
    <div class="text-overline text-rui-text-secondary">
      {{ t('balance_divergence.title') }}
    </div>
    <i18n-t
      keypath="data_issues.detail.divergence_scope"
      tag="p"
      class="text-body-2 text-rui-text-secondary"
      scope="global"
      data-testid="data-issue-divergence-scope"
    >
      <template #date>
        <DateDisplay
          :timestamp="issue.tsEnd"
          milliseconds
          class="text-rui-text"
        />
      </template>
    </i18n-t>
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
          {{ chainName }}
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
      :loading="loading || checkingArchive"
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
    <p
      v-if="nextStep"
      class="text-body-2"
      data-testid="data-issue-divergence-next-step"
    >
      {{ nextStep }}
    </p>
    <DivergenceBoundaryCard
      v-for="boundary in boundaries"
      :key="boundary.key"
      :boundary="boundary"
      :asset="issue.asset ?? undefined"
      :location="chain"
      @view="viewBoundary(boundary)"
    />
    <p
      v-if="error"
      class="text-body-2 text-rui-text-secondary"
      data-testid="data-issue-divergence-error"
    >
      {{ t('balance_divergence.search_failed') }}
    </p>
  </section>
</template>
