<script setup lang="ts">
import type { EditableMissingPrice, Report } from '@/modules/reports/report-types';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import ReportActionableCardActions from '@/modules/reports/ReportActionableCardActions.vue';
import {
  summarizeMissingPrices,
  useMissingPriceFinishPrompt,
  useReportActionableStepper,
} from '@/modules/reports/use-report-actionable-items';
import { useReportsStore } from '@/modules/reports/use-reports-store';
import { PinnedNames } from '@/modules/session/types';
import { usePinnedPanel } from '@/modules/shell/pinned/use-pinned-panel';

const {
  isPinned = false,
  report,
} = defineProps<{
  report: Report;
  isPinned?: boolean;
}>();

const emit = defineEmits<{
  'set-dialog': [value: boolean];
  'regenerate': [];
}>();

const ReportMissingAcquisitions = defineAsyncComponent(
  () => import('@/modules/reports/ReportMissingAcquisitions.vue'),
);
const ReportMissingPrices = defineAsyncComponent(() => import('@/modules/reports/ReportMissingPrices.vue'));

const { t } = useI18n({ useScope: 'global' });
const { pin: pinPanel, unpin: unpinPanel } = usePinnedPanel(PinnedNames.REPORT_ACTIONABLE_CARD);

function setDialog(dialog: boolean) {
  emit('set-dialog', dialog);
}

const reportsStore = useReportsStore();
const { actionableItems } = storeToRefs(reportsStore);

const { counts: actionableItemsLength, modelStep: step, steps: stepperContents } = useReportActionableStepper(
  actionableItems,
  { missingAcquisitions: ReportMissingAcquisitions, missingPrices: ReportMissingPrices },
);

function pinSection() {
  pinPanel({ isPinned: true, report });
  setDialog(false);
}

const { show } = useConfirmStore();
const { promptFor } = useMissingPriceFinishPrompt();

function submitActionableItems(missingPrices: EditableMissingPrice[]) {
  const { message, outcome, primaryAction, title, type } = promptFor(summarizeMissingPrices(missingPrices));

  show({ message, primaryAction, title, type }, () => {
    if (outcome === 'regenerate')
      regenerateReport();
    else ignoreIssues();
  });
}

function ignoreIssues() {
  if (isPinned)
    unpinPanel();

  setDialog(false);
}

function regenerateReport() {
  emit('regenerate');
}

function close() {
  if (isPinned)
    unpinPanel();
  else setDialog(false);
}
</script>

<template>
  <RuiCard
    no-padding
    class="overflow-hidden flex flex-col"
    :class="isPinned ? 'h-full rounded-none!' : 'max-h-[90vh]'"
    :class-names="{ content: 'flex flex-col flex-1 min-h-0 overflow-hidden' }"
    variant="flat"
  >
    <div
      v-if="!isPinned"
      class="flex items-center gap-1 pl-4 pr-2 py-2 border-b border-rui-divider shrink-0"
    >
      <h2
        class="grow text-base font-semibold text-rui-text"
        data-testid="report-actionable-title"
      >
        {{
          t('profit_loss_report.actionable.issues_found', {
            total: actionableItemsLength.total,
          })
        }}
      </h2>

      <RuiTooltip
        :options="{ placement: 'bottom' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            variant="text"
            icon
            size="sm"
            class="text-rui-text-secondary"
            :aria-label="t('profit_loss_report.actionable.actions.pin_section')"
            @click="pinSection()"
          >
            <RuiIcon
              name="lu-pin"
              size="18"
            />
          </RuiButton>
        </template>
        {{ t('profit_loss_report.actionable.actions.pin_section') }}
      </RuiTooltip>
      <RuiButton
        variant="text"
        icon
        size="sm"
        class="text-rui-text-secondary"
        :aria-label="t('common.actions.close')"
        @click="close()"
      >
        <RuiIcon
          name="lu-x"
          size="18"
        />
      </RuiButton>
    </div>

    <RuiStepper
      :steps="stepperContents"
      :step="step"
      class="border-b border-rui-divider shrink-0"
      :class="{ 'py-2': isPinned, 'py-3': !isPinned }"
    />

    <p
      v-if="stepperContents[step - 1]?.hint"
      class="shrink-0 text-sm text-rui-text-secondary border-b border-rui-divider"
      :class="isPinned ? 'px-3 py-2' : 'px-4 py-3'"
      data-testid="report-actionable-hint"
    >
      {{ stepperContents[step - 1]?.hint }}
    </p>

    <div
      class="flex-1 min-h-0 flex flex-col"
      :class="{ 'px-3': isPinned }"
    >
      <template
        v-for="(content, index) of stepperContents"
        :key="content.key"
      >
        <Component
          :is="content.selector"
          v-if="step === index + 1"
          :items="content.items"
          :is-pinned="isPinned"
          @pin="pinSection()"
        >
          <template #actions="{ items }">
            <ReportActionableCardActions
              :is-pinned="isPinned"
              :step="step"
              :total-steps="stepperContents.length"
              :is-missing-acquisitions="content.key === 'missingAcquisitions'"
              @back="step = step - 1"
              @next="step = step + 1"
              @close="setDialog(false)"
              @finish="submitActionableItems(items)"
            />
          </template>
        </Component>
      </template>
    </div>
  </RuiCard>
</template>
