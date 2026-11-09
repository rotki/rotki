<script setup lang="ts">
import type { StatusCounts } from '@/modules/history/reconciliation/schemas';
import ReconciliationCheckButton from '@/modules/history/reconciliation/components/ReconciliationCheckButton.vue';
import { HEADLINE_LABEL, SUBLINE_LABEL } from '@/modules/history/reconciliation/messages';
import { type Headline, headlineFor, notCheckedCount } from '@/modules/history/reconciliation/use-reconciliation-rows';
import TimeAgoDisplay from '@/modules/shell/components/display/TimeAgoDisplay.vue';

const {
  totals,
  lastComparedAt,
  detecting = false,
  disabled = false,
  stale = false,
  processing = false,
  checkError,
} = defineProps<{
  totals: StatusCounts;
  lastComparedAt: number | null;
  detecting?: boolean;
  disabled?: boolean;
  stale?: boolean;
  processing?: boolean;
  /** A refusal from the check request, such as history still processing (409). */
  checkError?: string;
}>();

const emit = defineEmits<{
  check: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const headline = computed<Headline>(() => headlineFor(totals));

const headlineColor = computed<string>(() => {
  switch (get(headline).kind) {
    case 'mismatch':
      return 'text-rui-error';
    case 'blocked':
      return 'text-rui-warning';
    case 'matches':
      return 'text-rui-success';
    default:
      return 'text-rui-text';
  }
});

const sublineCounts = computed<string[]>(() => countsParts(totals));

function countsParts(counts: StatusCounts): string[] {
  const parts: { count: number; key: keyof typeof SUBLINE_LABEL }[] = [
    { count: counts.reconciled, key: 'matches' },
    { count: counts.blocked, key: 'blocked' },
    { count: notCheckedCount(counts), key: 'not_checked' },
  ];
  return parts
    .filter(({ count }) => count > 0)
    .map(({ count, key }) => t(SUBLINE_LABEL[key], { count }, count));
}

const disabledReason = computed<string | undefined>(() => {
  if (processing)
    return t('data_issues.reconciliation.check.processing');
  if (stale)
    return t('data_issues.reconciliation.check.stale');
  return undefined;
});
</script>

<template>
  <div
    class="rounded-rui-card border border-default p-4 flex flex-col gap-3"
    data-testid="reconciliation-header"
  >
    <div class="flex flex-wrap items-start gap-4">
      <div class="flex flex-col gap-1 min-w-0 grow">
        <div
          class="text-xl font-medium"
          :class="headlineColor"
          data-testid="reconciliation-headline"
        >
          <template v-if="headline.kind === 'never'">
            {{ t('data_issues.reconciliation.headline.never') }}
          </template>
          <template v-else>
            {{ t(HEADLINE_LABEL[headline.kind], { count: headline.count }, headline.count) }}
          </template>
        </div>
        <div
          v-if="sublineCounts.length > 0"
          class="text-sm text-rui-text-secondary"
          data-testid="reconciliation-subline"
        >
          {{ sublineCounts.join(' · ') }}
        </div>
        <div class="text-xs text-rui-text-disabled">
          {{ t('data_issues.reconciliation.subline.explanation') }}
        </div>
      </div>

      <div class="flex flex-col items-end gap-2 shrink-0">
        <ReconciliationCheckButton
          :detecting="detecting"
          :disabled="disabled"
          :disabled-reason="disabledReason"
          @check="emit('check')"
        />
        <span
          v-if="lastComparedAt !== null"
          class="text-xs text-rui-text-secondary"
          data-testid="reconciliation-checked-at"
        >
          <i18n-t
            keypath="data_issues.reconciliation.check.checked"
            scope="global"
            tag="span"
          >
            <template #time>
              <TimeAgoDisplay :timestamp="lastComparedAt" />
            </template>
          </i18n-t>
        </span>
      </div>
    </div>

    <RuiAlert
      v-if="stale || processing"
      type="info"
      data-testid="reconciliation-recalculating"
    >
      {{ processing
        ? t('data_issues.reconciliation.recalculating.processing')
        : t('data_issues.reconciliation.recalculating.stale') }}
    </RuiAlert>

    <RuiAlert
      v-if="checkError"
      type="error"
      data-testid="reconciliation-check-error"
    >
      {{ checkError }}
    </RuiAlert>
  </div>
</template>
