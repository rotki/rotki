<script setup lang="ts">
import type { Component } from 'vue';
import type { DialogType } from '@/types/dialogs';
import type { EditableMissingPrice, MissingAcquisition, MissingPrice, Report } from '@/types/reports';
import type { Pinned } from '@/types/session';
import { type Nullable, toSentenceCase } from '@rotki/common';
import { useConfirmStore } from '@/store/confirm';
import { useReportsStore } from '@/store/reports';
import { useAreaVisibilityStore } from '@/store/session/visibility';

const props = withDefaults(
  defineProps<{
    report: Report;
    isPinned?: boolean;
  }>(),
  {
    isPinned: false,
  },
);

const emit = defineEmits<{
  (e: 'set-dialog', value: boolean): void;
  (e: 'regenerate'): void;
}>();
const ReportMissingAcquisitions = defineAsyncComponent(
  () => import('@/components/profitloss/ReportMissingAcquisitions.vue'),
);
const ReportMissingPrices = defineAsyncComponent(() => import('@/components/profitloss/ReportMissingPrices.vue'));

const { t } = useI18n({ useScope: 'global' });
const { isPinned, report } = toRefs(props);
const { pinned, showPinned } = storeToRefs(useAreaVisibilityStore());

function setDialog(dialog: boolean) {
  emit('set-dialog', dialog);
}

const reportsStore = useReportsStore();
const { actionableItems } = toRefs(reportsStore);

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

function setPinned(pin: Nullable<Pinned>) {
  set(pinned, pin);
}

function pinSection() {
  const pinned: Pinned = {
    name: 'report-actionable-card',
    props: {
      isPinned: true,
      report: get(report),
    },
  };

  setPinned(pinned);
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
  if (missingPricesLength >= 0) {
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
  if (get(isPinned))
    setPinned(null);

  setDialog(false);
}

function regenerateReport() {
  emit('regenerate');
}

function close() {
  if (get(isPinned))
    setPinned(null);
  else setDialog(false);
}

function closePinnedSidebar() {
  set(showPinned, false);
}
</script>

<template>
  <RuiCard
    no-padding
    class="overflow-hidden"
    :class="{ '!rounded-none': isPinned }"
    variant="flat"
  >
    <div class="flex bg-rui-primary text-white p-2">
      <RuiButton
        v-if="!isPinned"
        variant="text"
        icon
        @click="close()"
      >
        <RuiIcon
          class="text-white"
          name="lu-x"
        />
      </RuiButton>
      <RuiButton
        v-else
        variant="text"
        size="sm"
        icon
        @click="closePinnedSidebar()"
      >
        <RuiIcon
          class="text-white"
          name="lu-chevron-right"
          size="20"
        />
      </RuiButton>

      <h6
        class="flex items-center"
        :class="{
          'pl-2 text-h6': !isPinned,
          'text-body-1': isPinned,
        }"
      >
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
            :size="isPinned ? 'sm' : undefined"
            @click="isPinned ? setPinned(null) : pinSection()"
          >
            <RuiIcon
              v-if="isPinned"
              size="20"
              class="text-white"
              name="lu-pin-off"
            />
            <RuiIcon
              v-else
              class="text-white"
              name="lu-pin"
            />
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

    <RuiStepper
      :steps="stepperContents"
      :step="step"
      class="border-b-2 border-default"
      :class="{ 'py-2': isPinned, 'py-4': !isPinned }"
    />

    <div
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
        <template
          v-if="step === index + 1"
          #actions="{ items }"
        >
          <div
            class="border-t-2 border-rui-grey-300 dark:border-rui-grey-800 relative z-[2] flex items-center justify-between gap-4"
            :class="isPinned ? 'p-2' : 'p-4'"
          >
            <div
              v-if="content.hint"
              class="text-caption"
            >
              {{ content.hint }}
            </div>

            <div class="flex gap-2">
              <RuiButton
                v-if="step > 1"
                :size="isPinned ? 'sm' : undefined"
                variant="text"
                @click="step = step - 1"
              >
                {{ t('common.actions.back') }}
              </RuiButton>
              <RuiButton
                v-if="step < stepperContents.length"
                color="primary"
                :size="isPinned ? 'sm' : undefined"
                @click="step = step + 1"
              >
                {{ t('common.actions.next') }}
              </RuiButton>
              <template v-if="step === stepperContents.length">
                <RuiButton
                  v-if="!isPinned && content.key === 'missingAcquisitions'"
                  color="primary"
                  :size="isPinned ? 'sm' : undefined"
                  @click="setDialog(false)"
                >
                  {{ t('common.actions.close') }}
                </RuiButton>
                <RuiButton
                  v-else-if="content.key !== 'missingAcquisitions'"
                  color="primary"
                  :size="isPinned ? 'sm' : undefined"
                  @click="submitActionableItems(items)"
                >
                  {{ t('common.actions.finish') }}
                </RuiButton>
              </template>
            </div>
          </div>
        </template>
      </Component>
    </div>
  </RuiCard>
</template>
