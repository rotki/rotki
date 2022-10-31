<template>
  <div>
    <v-card elevation="0">
      <v-toolbar
        dark
        color="primary"
        :height="isPinned ? 40 : 'auto'"
        :class="{ [$style['pinned__toolbar']]: isPinned }"
      >
        <v-btn v-if="!isPinned" icon dark @click="close">
          <v-icon>mdi-close</v-icon>
        </v-btn>

        <v-toolbar-title
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
        </v-toolbar-title>

        <v-spacer />

        <v-tooltip bottom>
          <template #activator="{ on }">
            <v-btn
              icon
              dark
              :small="isPinned"
              v-on="on"
              @click="isPinned ? setPinned(null) : pinSection()"
            >
              <v-icon v-if="isPinned" :class="$style.pin" small>
                mdi-pin-off
              </v-icon>
              <v-icon v-else :class="$style.pin">mdi-pin</v-icon>
            </v-btn>
          </template>
          <span v-if="isPinned">
            {{ t('profit_loss_report.actionable.actions.unpin_section') }}
          </span>
          <span v-else>
            {{ t('profit_loss_report.actionable.actions.pin_section') }}
          </span>
        </v-tooltip>
      </v-toolbar>
      <div>
        <v-stepper v-model="step" elevation="0">
          <v-stepper-header
            :class="{
              [$style.raise]: true,
              [$style['pinned__stepper-header']]: isPinned
            }"
          >
            <template v-for="(content, index) of stepperContents">
              <v-stepper-step
                :key="content.key"
                :step="index + 1"
                :complete="step > index + 1"
                :class="{ [$style['pinned__stepper-step']]: isPinned }"
              >
                <span
                  v-if="
                    ($vuetify.breakpoint.mdAndUp && !isPinned) ||
                    step === index + 1
                  "
                >
                  {{ content.title }}
                </span>
              </v-stepper-step>
              <v-divider
                v-if="index < stepperContents.length - 1"
                :key="'divider-' + content.key"
              />
            </template>
          </v-stepper-header>
          <v-stepper-items>
            <template v-for="(content, index) of stepperContents">
              <v-stepper-content
                :key="content.key"
                :step="index + 1"
                class="pa-0"
              >
                <component
                  :is="content.selector"
                  :items="content.items"
                  :report="report"
                  :is-pinned="isPinned"
                >
                  <template v-if="step === index + 1" #actions="{ items }">
                    <v-sheet
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

                      <v-spacer />

                      <div
                        class="d-flex"
                        :class="isPinned ? 'flex-column' : ''"
                      >
                        <v-btn
                          v-if="step > 1"
                          :small="isPinned"
                          text
                          @click="step = step - 1"
                        >
                          {{ tc('common.actions.back') }}
                        </v-btn>
                        <v-btn
                          v-if="step < stepperContents.length"
                          class="ml-4"
                          color="primary"
                          :small="isPinned"
                          elevation="1"
                          @click="step = step + 1"
                        >
                          {{ tc('common.actions.next') }}
                        </v-btn>
                        <template v-if="step === stepperContents.length">
                          <v-btn
                            v-if="
                              !isPinned && content.key === 'missingAcquisitions'
                            "
                            color="primary"
                            :small="isPinned"
                            @click="setDialog(false)"
                          >
                            {{ tc('common.actions.close') }}
                          </v-btn>
                          <v-btn
                            v-else-if="content.key !== 'missingAcquisitions'"
                            :class="!isPinned ? 'ml-4' : ''"
                            color="primary"
                            :small="isPinned"
                            elevation="1"
                            @click="submitActionableItems(items)"
                          >
                            {{ tc('common.actions.finish') }}
                          </v-btn>
                        </template>
                      </div>
                    </v-sheet>
                  </template>
                </component>
              </v-stepper-content>
            </template>
          </v-stepper-items>
        </v-stepper>
      </div>
    </v-card>
    <v-dialog v-model="confirmationDialogOpen" :max-width="500">
      <card>
        <template #title>
          <div v-if="filledMissingPrices === 0">
            <v-icon class="mr-2" color="red">mdi-alert</v-icon>
            {{
              t('profit_loss_report.actionable.missing_prices.no_filled_prices')
            }}
          </div>
          <div v-else-if="skippedMissingPrices">
            <v-icon class="mr-2" color="red">mdi-alert</v-icon>
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
            <v-icon class="mr-2" color="green">mdi-check</v-icon>
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
              tc(
                'profit_loss_report.actionable.missing_prices.skipped_all_events_confirmation'
              )
            }}
          </div>
          <div v-else-if="skippedMissingPrices">
            {{ tc('profit_loss_report.actionable.missing_prices.if_sure') }}
            {{
              tc(
                'profit_loss_report.actionable.missing_prices.regenerate_report_nudge'
              )
            }}
          </div>
          <div v-else>
            {{
              toSentenceCase(
                tc(
                  'profit_loss_report.actionable.missing_prices.regenerate_report_nudge'
                )
              )
            }}
          </div>
        </div>
        <template #buttons>
          <v-spacer />
          <v-btn text class="mr-2" @click="confirmationDialogOpen = false">
            {{ tc('common.actions.cancel') }}
          </v-btn>
          <v-btn
            v-if="filledMissingPrices"
            color="primary"
            @click="regenerateReport"
          >
            {{ tc('profit_loss_report.actionable.actions.regenerate_report') }}
          </v-btn>
          <v-btn v-else color="primary" @click="ignoreIssues">
            {{ tc('common.actions.yes') }}
          </v-btn>
        </template>
      </card>
    </v-dialog>
  </div>
</template>
<script setup lang="ts">
import { Nullable } from '@rotki/common';
import { PropType } from 'vue';
import { useRouter } from '@/composables/router';
import { Routes } from '@/router/routes';
import { useReports } from '@/store/reports';
import { Pinned } from '@/store/session/types';
import { useAreaVisibilityStore } from '@/store/session/visibility';
import { EditableMissingPrice } from '@/types/prices';
import { SelectedReport } from '@/types/reports';
import { toSentenceCase } from '@/utils/text';

const props = defineProps({
  report: {
    required: true,
    type: Object as PropType<SelectedReport>
  },
  isPinned: { required: false, type: Boolean, default: false }
});

const emit = defineEmits<{ (e: 'set-dialog', value: boolean): void }>();
const { t, tc } = useI18n();
const { report, isPinned } = toRefs(props);
const router = useRouter();
const { pinned } = storeToRefs(useAreaVisibilityStore());

const setDialog = (dialog: boolean) => {
  emit('set-dialog', dialog);
};

const reportsStore = useReports();
const { actionableItems } = toRefs(reportsStore);

const actionableItemsLength = computed(() => {
  let missingAcquisitionsLength: number = 0;
  let missingPricesLength: number = 0;
  let total: number = 0;

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
      selector: 'report-missing-acquisitions',
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
      selector: 'report-missing-prices',
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
  const filled = missingPrices.filter((missingPrice: EditableMissingPrice) => {
    return !!missingPrice.price;
  }).length;
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

const regenerateReport = async () => {
  await router.push({
    path: Routes.PROFIT_LOSS_REPORTS.route,
    query: {
      regenerate: 'true',
      start: get(report).start.toString(),
      end: get(report).end.toString()
    }
  });
};

const close = () => {
  if (get(isPinned)) {
    setPinned(null);
  } else {
    setDialog(false);
  }
};
</script>
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
