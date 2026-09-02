<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import type { DataIssue } from '@/modules/history/data-issues/schemas';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import DataIssueDescription from '@/modules/history/data-issues/components/DataIssueDescription.vue';
import DataIssueDetectedTime from '@/modules/history/data-issues/components/DataIssueDetectedTime.vue';
import DataIssueKindChip from '@/modules/history/data-issues/components/DataIssueKindChip.vue';
import DataIssueRemediationTimeline from '@/modules/history/data-issues/components/DataIssueRemediationTimeline.vue';
import DataIssueStateChip from '@/modules/history/data-issues/components/DataIssueStateChip.vue';
import { canDismiss, canResolveManually, canRetry, IssueState } from '@/modules/history/data-issues/constants';
import { describeIssue, relatedEventRoute, toTimelineItems } from '@/modules/history/data-issues/transforms';
import HistoryEventAccount from '@/modules/history/events/HistoryEventAccount.vue';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import CounterpartyDisplay from '@/modules/shell/components/display/CounterpartyDisplay.vue';

/**
 * One issue's detail body, shared by both of its containers: the drawer on the data-issues page and
 * the bottom sheet in the pinned rail. Owns no open state, emitting `close` for each to interpret.
 */
const { issue, busy = false } = defineProps<{
  issue?: DataIssue;
  busy?: boolean;
}>();

const emit = defineEmits<{
  close: [];
  dismiss: [id: number];
  retry: [id: number];
  resolve: [id: number];
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const description = computed(() => issue ? describeIssue(issue) : undefined);

/** Deep-link to the offending history event (shared with the inbox panel). */
const relatedEventLink = computed<RouteLocationRaw | undefined>(() =>
  issue ? relatedEventRoute(issue.kind, get(description)?.eventIdentifier, issue.groupIdentifier, issue.asset) : undefined);

async function goToRelatedEvent(): Promise<void> {
  const link = get(relatedEventLink);
  if (!link)
    return;
  emit('close');
  await router.push(link);
}

const timeline = computed(() => (issue ? toTimelineItems(issue) : []));

const resolutionNote = computed<string | undefined>(() => {
  const resolution = issue?.payload?.resolution;
  if (resolution && typeof resolution === 'object' && 'note' in resolution) {
    const note = resolution.note;
    return typeof note === 'string' ? note : undefined;
  }
  return undefined;
});
</script>

<template>
  <div
    v-if="issue"
    class="flex flex-col h-full"
  >
    <div class="flex items-start justify-between gap-2 p-4 border-b border-default">
      <div class="flex flex-col gap-2">
        <h5 class="text-h6">
          {{ t('data_issues.detail.title') }}
        </h5>
        <div class="flex items-center gap-2 flex-wrap">
          <DataIssueKindChip :kind="issue.kind" />
          <DataIssueStateChip :state="issue.state" />
        </div>
      </div>
      <RuiButton
        variant="text"
        icon
        size="sm"
        @click="emit('close')"
      >
        <RuiIcon name="lu-x" />
      </RuiButton>
    </div>

    <div class="flex flex-col gap-6 p-4 overflow-y-auto grow">
      <section>
        <div class="text-overline text-rui-text-secondary mb-1">
          {{ t('data_issues.detail.whats_wrong') }}
        </div>
        <DataIssueDescription
          v-if="description"
          :description="description"
          tag="p"
          class="text-body-1"
        />
        <RuiButton
          v-if="description?.eventIdentifier !== undefined && relatedEventLink"
          variant="text"
          color="primary"
          size="sm"
          class="mt-1 !px-0"
          data-testid="data-issue-related-event"
          @click="goToRelatedEvent()"
        >
          <template #append>
            <RuiIcon
              name="lu-arrow-up-right"
              size="16"
            />
          </template>
          {{ t('data_issues.detail.related_event', { id: description.eventIdentifier }) }}
        </RuiButton>
      </section>

      <section class="grid grid-cols-2 gap-x-4 gap-y-5">
        <div class="flex flex-col gap-1">
          <div class="text-overline text-rui-text-secondary">
            {{ t('common.account') }}
          </div>
          <div class="flex items-center grow min-h-8">
            <HistoryEventAccount
              v-if="issue.locationLabel"
              :location="issue.location"
              :location-label="issue.locationLabel"
            />
            <span
              v-else
              class="text-body-2 text-rui-text-secondary"
            >
              -
            </span>
          </div>
        </div>
        <div class="flex flex-col gap-1">
          <div class="text-overline text-rui-text-secondary">
            {{ t('common.location') }}
          </div>
          <div class="flex items-center grow min-h-8">
            <LocationDisplay
              :identifier="issue.location"
              horizontal
              class="w-fit"
            />
          </div>
        </div>
        <div
          v-if="issue.asset"
          class="flex flex-col gap-1"
        >
          <div class="text-overline text-rui-text-secondary">
            {{ t('common.asset') }}
          </div>
          <div class="flex items-center grow min-h-8">
            <AssetDetails :asset="issue.asset" />
          </div>
        </div>
        <div
          v-if="issue.protocol"
          class="flex flex-col gap-1"
        >
          <div class="text-overline text-rui-text-secondary">
            {{ t('common.protocol') }}
          </div>
          <div class="flex items-center grow min-h-8">
            <CounterpartyDisplay :counterparty="issue.protocol" />
          </div>
        </div>
        <div class="flex flex-col gap-1">
          <div class="text-overline text-rui-text-secondary">
            {{ t('data_issues.detail.detected') }}
          </div>
          <div class="flex items-center grow min-h-8">
            <DataIssueDetectedTime :timestamp="issue.createdAt" />
          </div>
        </div>
      </section>

      <section>
        <div class="text-overline text-rui-text-secondary mb-2">
          {{ t('data_issues.detail.remediation_history') }}
        </div>
        <DataIssueRemediationTimeline :items="timeline" />
      </section>

      <section v-if="resolutionNote">
        <div class="text-overline text-rui-text-secondary mb-1">
          {{ t('data_issues.detail.resolution_note') }}
        </div>
        <p class="text-body-2">
          {{ resolutionNote }}
        </p>
      </section>
    </div>

    <div class="flex items-center justify-end gap-2 p-4 border-t border-default">
      <RuiButton
        variant="outlined"
        :disabled="busy || !canDismiss(issue.state)"
        data-testid="data-issue-detail-dismiss"
        @click="emit('dismiss', issue.id)"
      >
        {{ t('data_issues.action.dismiss.label') }}
      </RuiButton>
      <RuiButton
        v-if="canRetry(issue.kind, issue.state) || issue.state === IssueState.AUTO_REMEDIATING"
        variant="outlined"
        color="primary"
        :disabled="busy || !canRetry(issue.kind, issue.state)"
        data-testid="data-issue-detail-retry"
        @click="emit('retry', issue.id)"
      >
        {{ t('data_issues.action.retry.label') }}
      </RuiButton>
      <RuiButton
        color="primary"
        :disabled="busy || !canResolveManually(issue.state)"
        data-testid="data-issue-detail-resolve"
        @click="emit('resolve', issue.id)"
      >
        {{ t('data_issues.action.resolve.label') }}
      </RuiButton>
    </div>
  </div>
</template>
