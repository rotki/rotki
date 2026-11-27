<script setup lang="ts">
import type { SpamAssessment } from '@/modules/assets/spam/use-spam-assessments';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import { RuiButton, RuiIcon } from '@rotki/ui-library';
import { useI18n } from 'vue-i18n';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import SpamAssessmentHint from '@/modules/assets/spam/SpamAssessmentHint.vue';
import DataIssueKindChip from '@/modules/history/data-issues/components/DataIssueKindChip.vue';
import DataIssueStateChip from '@/modules/history/data-issues/components/DataIssueStateChip.vue';
import HistoryEventAccount from '@/modules/history/events/HistoryEventAccount.vue';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import CounterpartyDisplay from '@/modules/shell/components/display/CounterpartyDisplay.vue';
import TimeAgoDisplay from '@/modules/shell/components/display/TimeAgoDisplay.vue';

/** The detail's heading: title and close button, the issue's kind, state and age, and what it is about. */
const { issue, spamAssessment } = defineProps<{
  issue: DataIssue;
  spamAssessment?: SpamAssessment;
}>();

const emit = defineEmits<{
  close: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex flex-col gap-2 py-2 pl-4 pr-2 border-b border-rui-divider">
    <div class="flex items-center justify-between gap-2">
      <h2 class="text-base font-semibold text-rui-text">
        {{ t('data_issues.detail.title') }}
      </h2>
      <RuiButton
        variant="text"
        icon
        class="text-rui-text-secondary!"
        :aria-label="t('common.actions.close')"
        @click="emit('close')"
      >
        <RuiIcon name="lu-x" />
      </RuiButton>
    </div>
    <div class="flex flex-wrap items-center gap-2 text-xs text-rui-text-secondary">
      <DataIssueKindChip :kind="issue.kind" />
      <DataIssueStateChip :state="issue.state" />
      <span class="ml-1">
        {{ t('data_issues.detail.detected') }}
        <TimeAgoDisplay :timestamp="issue.createdAt" />
      </span>
    </div>
    <div
      class="flex flex-wrap items-center gap-x-5 gap-y-2 pb-2 text-sm"
      data-testid="data-issue-subject"
    >
      <span class="inline-flex items-center">
        <span class="sr-only">{{ t('common.account') }}</span>
        <HistoryEventAccount
          v-if="issue.locationLabel"
          :location="issue.location"
          :location-label="issue.locationLabel"
        />
        <span
          v-else
          class="text-rui-text-secondary"
        >
          -
        </span>
      </span>
      <span class="inline-flex items-center">
        <span class="sr-only">{{ t('common.location') }}</span>
        <LocationDisplay
          :identifier="issue.location"
          horizontal
          size="20px"
          class="w-fit"
        />
      </span>
      <span
        v-if="issue.asset"
        class="inline-flex items-center"
      >
        <span class="sr-only">{{ t('common.asset') }}</span>
        <AssetDetails
          :asset="issue.asset"
          :display="{ dense: true, inline: true, size: '20px' }"
        />
      </span>
      <span
        v-if="issue.asset && spamAssessment"
        class="inline-flex items-center gap-1.5 text-xs text-rui-text-secondary"
        data-testid="data-issue-spam-estimate"
      >
        <span>{{ t('spam_estimate.label') }}</span>
        <SpamAssessmentHint :assessment="spamAssessment" />
      </span>
      <span
        v-if="issue.protocol"
        class="inline-flex items-center"
      >
        <span class="sr-only">{{ t('common.protocol') }}</span>
        <CounterpartyDisplay :counterparty="issue.protocol" />
      </span>
    </div>
  </div>
</template>
