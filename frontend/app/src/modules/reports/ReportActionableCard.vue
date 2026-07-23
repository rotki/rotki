<script setup lang="ts">
import type { Component } from 'vue';
import type { DialogType } from '@/modules/core/common/dialogs';
import type { EditableMissingPrice, MissingAcquisition, MissingPrice, Report } from '@/modules/reports/report-types';
import { toSentenceCase } from '@rotki/common';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import ReportActionableCardActions from '@/modules/reports/ReportActionableCardActions.vue';
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

const step = ref<number>(1);

const actionableItemsLength = computed(() => {
  let missingAcquisitionsLength = 0;
  let missingPricesLength = 0;
  let total = 0;

  const items = get(actionableItems);

  if (items) {
    missingAcquisitionsLength = items.missingAcquisitions.length;
    missingPricesLength = items.missingPrices.length;
    total = missingAcquisitionsLength + missingPricesLength;
  }

  if (!missingAcquisitionsLength || !missingPricesLength)
    set(step, 1);

  return {
    missingAcquisitionsLength,
    missingPricesLength,
    total,
  };
});

function pinSection() {
  pinPanel({ isPinned: true, report });
  setDialog(false);
}

const stepperContents = computed<
  {
    key: string;
    title: string;
    hint: string;
    selector: Component;
    items: MissingAcquisition[] | MissingPrice[];
  }[]
>(() => {
  const contents = [];

  const missingAcquisitionsLength = get(actionableItemsLength).missingAcquisitionsLength;

  if (missingAcquisitionsLength > 0) {
    contents.push({
      hint: t('profit_loss_report.actionable.missing_acquisitions.hint'),
      items: get(actionableItems).missingAcquisitions,
      key: 'missingAcquisitions',
      selector: ReportMissingAcquisitions,
      title: t('profit_loss_report.actionable.missing_acquisitions.title', {
        total: missingAcquisitionsLength,
      }),
    });
  }

  const missingPricesLength = get(actionableItemsLength).missingPricesLength;
  if (missingPricesLength > 0) {
    contents.push({
      hint: t('profit_loss_report.actionable.missing_prices.hint'),
      items: get(actionableItems).missingPrices,
      key: 'missingPrices',
      selector: ReportMissingPrices,
      title: t('profit_loss_report.actionable.missing_prices.title', {
        total: missingPricesLength,
      }),
    });
  }

  return contents;
});

const totalMissingPrices = ref<number>(0);
const filledMissingPrices = ref<number>(0);
const skippedMissingPrices = ref<number>(0);

const { show } = useConfirmStore();

function showFinishDialog() {
  let type: DialogType = 'success';
  let title = t('profit_loss_report.actionable.missing_prices.all_prices_filled');
  let message = toSentenceCase(t('profit_loss_report.actionable.missing_prices.regenerate_report_nudge'));

  const filledMissingPricesVal = get(filledMissingPrices);
  const skippedMissingPricesVal = get(skippedMissingPrices);

  if (filledMissingPricesVal === 0) {
    type = 'warning';
    title = t('profit_loss_report.actionable.missing_prices.no_filled_prices');
    message = t('profit_loss_report.actionable.missing_prices.skipped_all_events_confirmation');
  }
  else if (skippedMissingPricesVal) {
    type = 'warning';
    title = t('profit_loss_report.actionable.missing_prices.total_skipped_prices', {
      total: skippedMissingPricesVal,
    });
    message = `${t('profit_loss_report.actionable.missing_prices.if_sure')} ${t(
      'profit_loss_report.actionable.missing_prices.regenerate_report_nudge',
    )}`;
  }

  const primaryAction = filledMissingPricesVal
    ? t('profit_loss_report.actionable.actions.regenerate_report')
    : t('common.actions.yes');

  show(
    {
      message,
      primaryAction,
      title,
      type,
    },
    () => {
      if (filledMissingPricesVal)
        regenerateReport();
      else ignoreIssues();
    },
  );
}

function submitActionableItems(missingPrices: EditableMissingPrice[]) {
  const total = missingPrices.length;
  const filled = missingPrices.filter((missingPrice: EditableMissingPrice) => !!missingPrice.price).length;
  set(totalMissingPrices, total);
  set(filledMissingPrices, filled);
  set(skippedMissingPrices, total - filled);

  showFinishDialog();
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
    content-class="flex flex-col flex-1 min-h-0 overflow-hidden"
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
        :popper="{ placement: 'bottom' }"
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
