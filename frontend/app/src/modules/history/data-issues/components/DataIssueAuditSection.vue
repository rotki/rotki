<script setup lang="ts">
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { RuiIcon } from '@rotki/ui-library';
import { get } from '@vueuse/shared';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { extractIssueResolution, isManuallyConfirmed } from '@/modules/history/data-issues/pnl-transforms';
import { useDataIssuesFormat } from '@/modules/history/data-issues/use-data-issues-format';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

const { issue } = defineProps<{
  issue: DataIssue;
}>();

const { t } = useI18n({ useScope: 'global' });
const { dispositionLabel } = useDataIssuesFormat();

const manualConfirmed = computed<boolean>(() => isManuallyConfirmed(issue));
const resolution = computed(() => extractIssueResolution(issue));
const resolutionDisposition = computed<string | undefined>(() => {
  const value = get(resolution)?.disposition;
  return value ? (dispositionLabel(value) ?? value) : undefined;
});

const resolutionNote = computed<string | undefined>(() => {
  const raw = issue.payload?.resolution;
  if (raw && typeof raw === 'object' && 'note' in raw) {
    const note = raw.note;
    return typeof note === 'string' ? note : undefined;
  }
  return undefined;
});
</script>

<template>
  <section
    v-if="manualConfirmed"
    class="flex flex-col gap-2"
    data-testid="data-issue-confirmed-audit"
  >
    <h3 class="text-xs font-medium text-rui-text-secondary flex items-center gap-1.5">
      <RuiIcon
        name="lu-shield-check"
        color="success"
        size="14"
      />
      {{ t('data_issues.detail.confirmed_title') }}
    </h3>
    <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-rui-text-secondary">
      <span
        v-if="resolutionDisposition"
        class="font-medium text-rui-text"
        data-testid="data-issue-confirmed-disposition"
      >
        {{ resolutionDisposition }}
      </span>
      <span
        v-if="issue.resolvedAt"
        data-testid="data-issue-confirmed-at"
      >
        {{ t('data_issues.detail.confirmed_at') }}
        <DateDisplay :timestamp="issue.resolvedAt" />
      </span>
    </div>
    <p
      v-if="resolutionNote"
      class="text-sm text-rui-text"
    >
      {{ resolutionNote }}
    </p>
  </section>

  <section
    v-else-if="resolutionNote"
    class="flex flex-col gap-2"
  >
    <h3 class="text-xs font-medium text-rui-text-secondary">
      {{ t('data_issues.detail.resolution_note') }}
    </h3>
    <p class="text-sm">
      {{ resolutionNote }}
    </p>
  </section>
</template>
