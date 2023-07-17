<script setup lang="ts">
import { type Nullable } from '@rotki/common';
import { type PropType } from 'vue';
import {
  type EditableMissingPrice,
  type SelectedReport
} from '@/types/reports';
import { toSentenceCase } from '@/utils/text';
import { type Pinned } from '@/types/session';

const props = defineProps({
  report: {
    required: true,
    type: Object as PropType<SelectedReport>
  },
  isPinned: { required: false, type: Boolean, default: false }
});
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
const confirmationDialogOpen = ref<boolean>(false);

const submitActionableItems = (missingPrices: EditableMissingPrice[]) => {
  const total = missingPrices.length;
  const filled = missingPrices.filter(
    (missingPrice: EditableMissingPrice) => !!missingPrice.price
  ).length;
  set(totalMissingPrices, total);
  set(filledMissingPrices, filled);
  set(skippedMissingPrices, total - filled);

  set(confirmationDialogOpen, true);
};

const ignoreIssues = () => {
  if (get(isPinned)) {
    setPinned(null);
  }
  set(confirmationDialogOpen, false);
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
    <VCard elevation="0">
      <VToolbar
        dark
        color="primary"
        :height="isPinned ? 40 : 'auto'"
        :class="{ [$style['pinned__toolbar']]: isPinned }"
      >
        <VBtn v-if="!isPinned" icon dark @click="close()">
          <VIcon>mdi-close</VIcon>
        </VBtn>

        <VToolbarTitle
          :class="{
            [$style['pinned__toolbar-title']]: isPinned,
            'pl-2': !isPinned
          }"
        >
          {{
            t('profit_loss_report.actionable.issues_found', {
              total: actionableItemsLength.total
            })
          }}
        </VToolbarTitle>

        <VSpacer />

        <VTooltip bottom>
          <template #activator="{ on }">
            <VBtn
              icon
              dark
              :small="isPinned"
              v-on="on"
              @click="isPinned ? setPinned(null) : pinSection()"
            >
              <VIcon v-if="isPinned" :class="$style.pin" small>
                mdi-pin-off
              </VIcon>
              <VIcon v-else :class="$style.pin">mdi-pin</VIcon>
            </VBtn>
          </template>
          <span v-if="isPinned">
            {{ t('profit_loss_report.actionable.actions.unpin_section') }}
          </span>
          <span v-else>
            {{ t('profit_loss_report.actionable.actions.pin_section') }}
          </span>
        </VTooltip>
      </VToolbar>
      <div>
        <VStepper v-model="step" elevation="0">
          <VStepperHeader
            :class="{
              [$style.raise]: true,
              [$style['pinned__stepper-header']]: isPinned
            }"
          >
            <template v-for="(content, index) of stepperContents">
              <VStepperStep
                :key="content.key"
                :step="index + 1"
                :complete="step > index + 1"
                :class="{ [$style['pinned__stepper-step']]: isPinned }"
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
              <VStepperContent
                :key="content.key"
                :step="index + 1"
                class="pa-0"
              >
                <Component
                  :is="content.selector"
                  :items="content.items"
                  :report="report"
                  :is-pinned="isPinned"
                >
                  <template v-if="step === index + 1" #actions="{ items }">
                    <VSheet
                      elevation="10"
                      class="d-flex align-center"
                      :class="{
                        [$style.raise]: true,
                        'pa-2': isPinned,
                        'pa-4': !isPinned
                      }"
                    >
                      <small v-if="content.hint" class="pr-4">
                        {{ content.hint }}
                      </small>

                      <VSpacer />

                      <div
                        class="d-flex"
                        :class="isPinned ? 'flex-column' : ''"
                      >
                        <VBtn
                          v-if="step > 1"
                          :small="isPinned"
                          text
                          @click="step = step - 1"
                        >
                          {{ t('common.actions.back') }}
                        </VBtn>
                        <VBtn
                          v-if="step < stepperContents.length"
                          class="ml-4"
                          color="primary"
                          :small="isPinned"
                          elevation="1"
                          @click="step = step + 1"
                        >
                          {{ t('common.actions.next') }}
                        </VBtn>
                        <template v-if="step === stepperContents.length">
                          <VBtn
                            v-if="
                              !isPinned && content.key === 'missingAcquisitions'
                            "
                            color="primary"
                            :small="isPinned"
                            @click="setDialog(false)"
                          >
                            {{ t('common.actions.close') }}
                          </VBtn>
                          <VBtn
                            v-else-if="content.key !== 'missingAcquisitions'"
                            :class="!isPinned ? 'ml-4' : ''"
                            color="primary"
                            :small="isPinned"
                            elevation="1"
                            @click="submitActionableItems(items)"
                          >
                            {{ t('common.actions.finish') }}
                          </VBtn>
                        </template>
                      </div>
                    </VSheet>
                  </template>
                </Component>
              </VStepperContent>
            </template>
          </VStepperItems>
        </VStepper>
      </div>
    </VCard>
    <VDialog v-model="confirmationDialogOpen" :max-width="500">
      <Card>
        <template #title>
          <div v-if="filledMissingPrices === 0">
            <VIcon class="mr-2" color="red">mdi-alert</VIcon>
            {{
              t('profit_loss_report.actionable.missing_prices.no_filled_prices')
            }}
          </div>
          <div v-else-if="skippedMissingPrices">
            <VIcon class="mr-2" color="red">mdi-alert</VIcon>
            {{
              t(
                'profit_loss_report.actionable.missing_prices.total_skipped_prices',
                {
                  total: skippedMissingPrices
                }
              )
            }}
          </div>
          <div v-else>
            <VIcon class="mr-2" color="green">mdi-check</VIcon>
            {{
              t(
                'profit_loss_report.actionable.missing_prices.all_prices_filled'
              )
            }}
          </div>
        </template>
        <div>
          <div v-if="filledMissingPrices === 0">
            {{
              t(
                'profit_loss_report.actionable.missing_prices.skipped_all_events_confirmation'
              )
            }}
          </div>
          <div v-else-if="skippedMissingPrices">
            {{ t('profit_loss_report.actionable.missing_prices.if_sure') }}
            {{
              t(
                'profit_loss_report.actionable.missing_prices.regenerate_report_nudge'
              )
            }}
          </div>
          <div v-else>
            {{
              toSentenceCase(
                t(
                  'profit_loss_report.actionable.missing_prices.regenerate_report_nudge'
                )
              )
            }}
          </div>
        </div>
        <template #buttons>
          <VSpacer />
          <VBtn text class="mr-2" @click="confirmationDialogOpen = false">
            {{ t('common.actions.cancel') }}
          </VBtn>
          <VBtn
            v-if="filledMissingPrices"
            color="primary"
            @click="regenerateReport()"
          >
            {{ t('profit_loss_report.actionable.actions.regenerate_report') }}
          </VBtn>
          <VBtn v-else color="primary" @click="ignoreIssues()">
            {{ t('common.actions.yes') }}
          </VBtn>
        </template>
      </Card>
    </VDialog>
  </div>
</template>

<style module lang="scss">
.pinned {
  &__toolbar {
    border-radius: 0 !important;

    &-title {
      font-size: 1rem;
    }
  }

  &__stepper {
    &-header {
      height: auto;
    }

    &-step {
      padding: 12px;
    }
  }
}

.pin {
  transform: rotate(20deg);
}

.raise {
  position: relative;
  z-index: 2;
}
</style>
