<script setup lang="ts">
import { type Nullable } from '@rotki/common';
import {
  type EditableMissingPrice,
  type SelectedReport
} from '@/types/reports';
import { toSentenceCase } from '@/utils/text';
import { type Pinned } from '@/types/session';
import { type DialogType } from '@/types/dialogs';

const props = withDefaults(
  defineProps<{
    report: SelectedReport;
    isPinned?: boolean;
  }>(),
  {
    isPinned: false
  }
);

const emit = defineEmits<{
  (e: 'set-dialog', value: boolean): void;
  (e: 'regenerate'): void;
}>();
const ReportMissingAcquisitions = defineAsyncComponent(
  () => import('@/components/profitloss/ReportMissingAcquisitions.vue')
);
const ReportMissingPrices = defineAsyncComponent(
  () => import('@/components/profitloss/ReportMissingPrices.vue')
);

const { t } = useI18n();
const { report, isPinned } = toRefs(props);
const { pinned } = storeToRefs(useAreaVisibilityStore());

const setDialog = (dialog: boolean) => {
  emit('set-dialog', dialog);
};

const reportsStore = useReportsStore();
const { actionableItems } = toRefs(reportsStore);

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

  if (!missingAcquisitionsLength || !missingPricesLength) {
    set(step, 1);
  }

  return {
    missingAcquisitionsLength,
    missingPricesLength,
    total
  };
});

const setPinned = (pin: Nullable<Pinned>) => {
  set(pinned, pin);
};

const pinSection = () => {
  const pinned: Pinned = {
    name: 'report-actionable-card',
    props: {
      report: get(report),
      isPinned: true
    }
  };

  setPinned(pinned);
  setDialog(false);
};

const step = ref<number>(1);

const stepperContents = computed(() => {
  const contents = [];

  const missingAcquisitionsLength = get(
    actionableItemsLength
  ).missingAcquisitionsLength;
  if (missingAcquisitionsLength > 0) {
    contents.push({
      key: 'missingAcquisitions',
      title: t('profit_loss_report.actionable.missing_acquisitions.title', {
        total: missingAcquisitionsLength
      }).toString(),
      hint: t(
        'profit_loss_report.actionable.missing_acquisitions.hint'
      ).toString(),
      selector: ReportMissingAcquisitions,
      items: get(actionableItems).missingAcquisitions
    });
  }

  const missingPricesLength = get(actionableItemsLength).missingPricesLength;
  if (missingPricesLength > 0) {
    contents.push({
      key: 'missingPrices',
      title: t('profit_loss_report.actionable.missing_prices.title', {
        total: missingPricesLength
      }).toString(),
      hint: t('profit_loss_report.actionable.missing_prices.hint').toString(),
      selector: ReportMissingPrices,
      items: get(actionableItems).missingPrices
    });
  }

  return contents;
});

const totalMissingPrices = ref<number>(0);
const filledMissingPrices = ref<number>(0);
const skippedMissingPrices = ref<number>(0);

const { show } = useConfirmStore();

const showFinishDialog = () => {
  let type: DialogType = 'success';
  let title = t(
    'profit_loss_report.actionable.missing_prices.all_prices_filled'
  );
  let message = toSentenceCase(
    t('profit_loss_report.actionable.missing_prices.regenerate_report_nudge')
  );

  const filledMissingPricesVal = get(filledMissingPrices);
  const skippedMissingPricesVal = get(skippedMissingPrices);

  if (filledMissingPricesVal === 0) {
    type = 'warning';
    title = t('profit_loss_report.actionable.missing_prices.no_filled_prices');
    message = t(
      'profit_loss_report.actionable.missing_prices.skipped_all_events_confirmation'
    );
  } else if (skippedMissingPricesVal) {
    type = 'warning';
    title = t(
      'profit_loss_report.actionable.missing_prices.total_skipped_prices',
      {
        total: skippedMissingPricesVal
      }
    );
    message = `${t('profit_loss_report.actionable.missing_prices.if_sure')} ${t(
      'profit_loss_report.actionable.missing_prices.regenerate_report_nudge'
    )}`;
  }

  const primaryAction = filledMissingPricesVal
    ? t('profit_loss_report.actionable.actions.regenerate_report')
    : t('common.actions.yes');

  show(
    {
      type,
      title,
      message,
      primaryAction
    },
    () => {
      if (filledMissingPricesVal) {
        regenerateReport();
      } else {
        ignoreIssues();
      }
    }
  );
};

const submitActionableItems = (missingPrices: EditableMissingPrice[]) => {
  const total = missingPrices.length;
  const filled = missingPrices.filter(
    (missingPrice: EditableMissingPrice) => !!missingPrice.price
  ).length;
  set(totalMissingPrices, total);
  set(filledMissingPrices, filled);
  set(skippedMissingPrices, total - filled);

  showFinishDialog();
};

const ignoreIssues = () => {
  if (get(isPinned)) {
    setPinned(null);
  }
  setDialog(false);
};

const regenerateReport = () => {
  emit('regenerate');
};

const close = () => {
  if (get(isPinned)) {
    setPinned(null);
  } else {
    setDialog(false);
  }
};

const { mdAndUp } = useDisplay();
</script>

<template>
  <div>
    <div class="flex bg-rui-primary text-white p-2">
      <RuiButton v-if="!isPinned" variant="text" icon @click="close()">
        <RuiIcon class="text-white" name="close-line" />
      </RuiButton>

      <h6
        class="flex items-center"
        :class="{
          'pl-2 text-h6': !isPinned,
          'text-body-1': isPinned
        }"
      >
        {{
          t('profit_loss_report.actionable.issues_found', {
            total: actionableItemsLength.total
          })
        }}
      </h6>

      <VSpacer />

      <RuiTooltip :popper="{ placement: 'bottom' }" open-delay="400">
        <template #activator>
          <RuiButton
            variant="text"
            icon
            :size="isPinned ? 'sm' : 'md'"
            @click="isPinned ? setPinned(null) : pinSection()"
          >
            <RuiIcon
              v-if="isPinned"
              size="20"
              class="text-white"
              name="unpin-line"
            />
            <RuiIcon v-else class="text-white" name="pushpin-line" />
          </RuiButton>
        </template>
        <span v-if="isPinned">
          {{ t('profit_loss_report.actionable.actions.unpin_section') }}
        </span>
        <span v-else>
          {{ t('profit_loss_report.actionable.actions.pin_section') }}
        </span>
      </RuiTooltip>
    </div>
    <VStepper v-model="step" class="!rounded-none">
      <VStepperHeader
        :class="{ 'h-auto': isPinned }"
        class="border-b-2 border-rui-grey-300 dark:border-rui-grey-800 shadow-none"
      >
        <template v-for="(content, index) of stepperContents">
          <VStepperStep
            :key="content.key"
            :step="index + 1"
            :complete="step > index + 1"
            :class="{ 'p-2': isPinned }"
          >
            <span v-if="(mdAndUp && !isPinned) || step === index + 1">
              {{ content.title }}
            </span>
          </VStepperStep>
          <VDivider
            v-if="index < stepperContents.length - 1"
            :key="'divider-' + content.key"
          />
        </template>
      </VStepperHeader>
      <VStepperItems>
        <template v-for="(content, index) of stepperContents">
          <VStepperContent :key="content.key" :step="index + 1" class="pa-0">
            <Component
              :is="content.selector"
              :items="content.items"
              :report="report"
              :is-pinned="isPinned"
            >
              <template v-if="step === index + 1" #actions="{ items }">
                <div
                  class="border-t-2 border-rui-grey-300 dark:border-rui-grey-800 relative z-[2] flex items-center justify-between gap-4"
                  :class="isPinned ? 'p-2' : 'p-4'"
                >
                  <div v-if="content.hint" class="text-caption">
                    {{ content.hint }}
                  </div>

                  <div class="flex gap-2">
                    <RuiButton
                      v-if="step > 1"
                      :size="isPinned ? 'sm' : 'md'"
                      variant="text"
                      @click="step = step - 1"
                    >
                      {{ t('common.actions.back') }}
                    </RuiButton>
                    <RuiButton
                      v-if="step < stepperContents.length"
                      color="primary"
                      :size="isPinned ? 'sm' : 'md'"
                      @click="step = step + 1"
                    >
                      {{ t('common.actions.next') }}
                    </RuiButton>
                    <template v-if="step === stepperContents.length">
                      <RuiButton
                        v-if="
                          !isPinned && content.key === 'missingAcquisitions'
                        "
                        color="primary"
                        :size="isPinned ? 'sm' : 'md'"
                        @click="setDialog(false)"
                      >
                        {{ t('common.actions.close') }}
                      </RuiButton>
                      <RuiButton
                        v-else-if="content.key !== 'missingAcquisitions'"
                        color="primary"
                        :size="isPinned ? 'sm' : 'md'"
                        @click="submitActionableItems(items)"
                      >
                        {{ t('common.actions.finish') }}
                      </RuiButton>
                    </template>
                  </div>
                </div>
              </template>
            </Component>
          </VStepperContent>
        </template>
      </VStepperItems>
    </VStepper>
  </div>
</template>
