<template>
  <div v-if="actionableItemsLength.total">
    <v-dialog v-model="mainDialogOpen" max-width="1000">
      <template #activator="{ on }">
        <v-btn color="error" depressed v-on="on" @click="step = 1">
          <span class="px-2">
            {{ $tc('profit_loss_report.actionable.show_issues') }}
          </span>
          <v-chip x-small class="px-2" color="error darken-2">
            {{ actionableItemsLength.total }}
          </v-chip>
        </v-btn>
      </template>
      <v-card>
        <v-toolbar dark color="primary">
          <v-btn icon dark @click="mainDialogOpen = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>

          <v-toolbar-title class="pl-2">
            {{
              $t('profit_loss_report.actionable.issues_found', {
                total: actionableItemsLength.total
              })
            }}
          </v-toolbar-title>
        </v-toolbar>
        <div>
          <v-stepper v-model="step">
            <v-stepper-header :class="$style.raise">
              <template v-for="(content, index) of stepperContents">
                <v-stepper-step
                  :key="content.key"
                  :step="index + 1"
                  :complete="step > index + 1"
                >
                  {{ content.title }}
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
                  >
                    <template v-if="step === index + 1" #actions="{ items }">
                      <v-sheet
                        elevation="10"
                        class="pa-4 d-flex align-center"
                        :class="$style.raise"
                      >
                        <small v-if="content.hint" class="pr-4">
                          {{ content.hint }}
                        </small>

                        <v-spacer />

                        <v-btn v-if="step > 1" text @click="step = step - 1">
                          {{
                            $tc('profit_loss_report.actionable.actions.back')
                          }}
                        </v-btn>
                        <v-btn
                          v-if="step < stepperContents.length"
                          class="ml-4"
                          color="primary"
                          @click="step = step + 1"
                        >
                          {{
                            $tc('profit_loss_report.actionable.actions.next')
                          }}
                        </v-btn>
                        <template v-if="step === stepperContents.length">
                          <v-btn
                            v-if="content.key === 'missingAcquisitions'"
                            class="ml-4"
                            color="primary"
                            @click="mainDialogOpen = false"
                          >
                            {{
                              $tc('profit_loss_report.actionable.actions.close')
                            }}
                          </v-btn>
                          <v-btn
                            v-else
                            class="ml-4"
                            color="primary"
                            @click="submitActionableItems(items)"
                          >
                            {{
                              $tc(
                                'profit_loss_report.actionable.actions.finish'
                              )
                            }}
                          </v-btn>
                        </template>
                      </v-sheet>
                    </template>
                  </component>
                </v-stepper-content>
              </template>
            </v-stepper-items>
          </v-stepper>
        </div>
      </v-card>
    </v-dialog>
    <v-dialog v-model="confirmationDialogOpen" :max-width="500">
      <card>
        <template #title>
          <div v-if="filledMissingPrices === 0">
            <v-icon class="mr-2" color="red">mdi-alert</v-icon>
            {{
              $tc(
                'profit_loss_report.actionable.missing_prices.no_filled_prices'
              )
            }}
          </div>
          <div v-else-if="skippedMissingPrices">
            <v-icon class="mr-2" color="red">mdi-alert</v-icon>
            {{
              $t(
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
              $tc(
                'profit_loss_report.actionable.missing_prices.all_prices_filled'
              )
            }}
          </div>
        </template>
        <div>
          <div v-if="filledMissingPrices === 0">
            {{
              $tc(
                'profit_loss_report.actionable.missing_prices.skipped_all_events_confirmation'
              )
            }}
          </div>
          <div v-else-if="skippedMissingPrices">
            {{ $tc('profit_loss_report.actionable.missing_prices.if_sure') }}
            {{
              $tc(
                'profit_loss_report.actionable.missing_prices.regenerate_report_nudge'
              )
            }}
          </div>
          <div v-else>
            {{
              toSentenceCase(
                $tc(
                  'profit_loss_report.actionable.missing_prices.regenerate_report_nudge'
                )
              )
            }}
          </div>
        </div>
        <template #buttons>
          <v-spacer />
          <v-btn text class="mr-2" @click="confirmationDialogOpen = false">
            {{ $tc('profit_loss_report.actionable.actions.cancel') }}
          </v-btn>
          <v-btn
            v-if="filledMissingPrices"
            color="primary"
            @click="regenerateReport"
          >
            {{ $tc('profit_loss_report.actionable.actions.regenerate_report') }}
          </v-btn>
          <v-btn v-else color="primary" @click="ignoreIssues">
            {{ $tc('profit_loss_report.actionable.actions.yes') }}
          </v-btn>
        </template>
      </card>
    </v-dialog>
  </div>
</template>
<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  ref,
  toRefs
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import ReportMissingAcquisitions from '@/components/profitloss/ReportMissingAcquisitions.vue';
import ReportMissingPrices, {
  EditableMissingPrice
} from '@/components/profitloss/ReportMissingPrices.vue';
import { useRouter } from '@/composables/common';
import i18n from '@/i18n';
import { Routes } from '@/router/routes';
import { useReports } from '@/store/reports';
import { SelectedReport } from '@/types/reports';
import { toSentenceCase } from '@/utils/text';

export default defineComponent({
  name: 'ReportActionable',
  components: {
    ReportMissingAcquisitions,
    ReportMissingPrices
  },
  props: {
    report: {
      required: true,
      type: Object as PropType<SelectedReport>
    },
    initialOpen: { required: false, type: Boolean, default: false }
  },
  setup(props) {
    const { report, initialOpen } = toRefs(props);
    const mainDialogOpen = ref<boolean>(get(initialOpen));

    const reportsStore = useReports();
    const { actionableItems } = reportsStore;

    const router = useRouter();

    const actionableItemsLength = computed(() => {
      let missingAcquisitionsLength: number = 0;
      let missingPricesLength: number = 0;
      let total: number = 0;

      const items = get(actionableItems);

      if (get(actionableItems)) {
        missingAcquisitionsLength = items.missingAcquisitions.length;
        missingPricesLength = items.missingPrices.length;
        total = missingAcquisitionsLength + missingPricesLength;
      }

      return {
        missingAcquisitionsLength,
        missingPricesLength,
        total
      };
    });

    const step = ref<number>(1);

    const stepperContents = computed(() => {
      const contents = [];

      const missingAcquisitionsLength = get(
        actionableItemsLength
      ).missingAcquisitionsLength;
      if (missingAcquisitionsLength > 0) {
        contents.push({
          key: 'missingAcquisitions',
          title: i18n
            .t('profit_loss_report.actionable.missing_acquisitions.title', {
              total: missingAcquisitionsLength
            })
            .toString(),
          hint: i18n
            .t('profit_loss_report.actionable.missing_acquisitions.hint')
            .toString(),
          selector: 'report-missing-acquisitions',
          items: get(actionableItems).missingAcquisitions
        });
      }

      const missingPricesLength = get(
        actionableItemsLength
      ).missingPricesLength;
      if (missingPricesLength > 0) {
        contents.push({
          key: 'missingPrices',
          title: i18n
            .t('profit_loss_report.actionable.missing_prices.title', {
              total: missingPricesLength
            })
            .toString(),
          hint: i18n
            .t('profit_loss_report.actionable.missing_prices.hint')
            .toString(),
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
      const filled = missingPrices.filter(
        (missingPrice: EditableMissingPrice) => {
          return !!missingPrice.price;
        }
      ).length;
      set(totalMissingPrices, total);
      set(filledMissingPrices, filled);
      set(skippedMissingPrices, total - filled);

      set(confirmationDialogOpen, true);
    };

    const ignoreIssues = () => {
      set(confirmationDialogOpen, false);
      set(mainDialogOpen, false);
    };

    const regenerateReport = () => {
      router.push({
        path: Routes.PROFIT_LOSS_REPORTS.route,
        query: {
          regenerate: 'true',
          start: get(report).start.toString(),
          end: get(report).end.toString()
        }
      });
    };

    return {
      mainDialogOpen,
      step,
      stepperContents,
      actionableItemsLength,
      submitActionableItems,
      totalMissingPrices,
      filledMissingPrices,
      skippedMissingPrices,
      confirmationDialogOpen,
      ignoreIssues,
      regenerateReport,
      toSentenceCase
    };
  }
});
</script>
<style module lang="scss">
.raise {
  position: relative;
  z-index: 2;
}
</style>
