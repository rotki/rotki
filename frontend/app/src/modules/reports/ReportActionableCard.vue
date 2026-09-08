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
    :class="isPinned ? 'h-full !rounded-none' : 'max-h-[90vh]'"
    :class-names="{ content: 'flex flex-col flex-1 min-h-0 overflow-hidden' }"
    variant="flat"
  >
    <!-- Dialog mode keeps its own header; when pinned, the rail's tab provides title + close. -->
    <div
      v-if="!isPinned"
      class="flex bg-rui-primary text-white p-2 shrink-0"
    >
      <RuiButton
        variant="text"
        icon
        @click="close()"
      >
        <RuiIcon
          class="text-white"
          name="lu-x"
        />
      </RuiButton>

      <h6 class="flex items-center pl-2 text-h6">
        {{
          t('profit_loss_report.actionable.issues_found', {
            total: actionableItemsLength.total,
          })
        }}
      </h6>

      <div class="grow" />

      <RuiTooltip
        :options="{ placement: 'bottom' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            variant="text"
            icon
            @click="pinSection()"
          >
            <RuiIcon
              class="text-white"
              name="lu-pin"
            />
          </RuiButton>
        </template>
        {{ t('profit_loss_report.actionable.actions.pin_section') }}
      </RuiTooltip>
    </div>

    <RuiStepper
      :steps="stepperContents"
      :step="step"
      class="border-b-2 border-default shrink-0"
      :class="{ 'py-2': isPinned, 'py-4': !isPinned }"
    />

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
              :hint="content.hint"
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
