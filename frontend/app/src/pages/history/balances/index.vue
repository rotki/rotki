<script setup lang="ts">
import { NoteLocation } from '@/modules/core/common/notes';
import { useRefWithDebounce } from '@/modules/core/common/use-ref-debounce';
import { TaskType } from '@/modules/core/tasks/task-type';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';
import HistoricalBalancesContent from '@/modules/history/balances/HistoricalBalancesContent.vue';
import NegativeBalancesDialog from '@/modules/history/balances/NegativeBalancesDialog.vue';
import { useHistoricalBalances } from '@/modules/history/balances/use-historical-balances';
import { useHistoricalBalancesStore } from '@/modules/history/balances/use-historical-balances-store';
import { usePremium } from '@/modules/premium/use-premium';
import CardTitle from '@/modules/shell/components/CardTitle.vue';
import GetPremiumPlaceholder from '@/modules/shell/components/GetPremiumPlaceholder.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

definePage({
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.HISTORY,
  },
  name: 'history-balances',
  redirect: '/history/events',
});

const { t } = useI18n({ useScope: 'global' });
const premium = usePremium();

const historicalBalancesStore = useHistoricalBalancesStore();
const { isProcessing, negativeBalances, processingPercentage, processingProgress } = storeToRefs(historicalBalancesStore);
const { triggerHistoricalBalancesProcessing } = useHistoricalBalances();

const { useIsTaskRunning } = useTaskStore();
const isProcessingTaskRunning = useIsTaskRunning(TaskType.PROCESS_HISTORICAL_BALANCES);

const negativeBalancesCount = computed<number>(() => get(negativeBalances).length);

const showNegativeBalancesDialog = ref<boolean>(false);

const hasNegativeBalances = useRefWithDebounce(
  computed<boolean>(() => get(negativeBalancesCount) > 0),
  300,
);
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.history'), t('historical_balances.title')]">
    <RuiCard>
      <template #custom-header>
        <div class="p-4 flex items-center justify-between">
          <div>
            <CardTitle>
              {{ t('historical_balances.title') }}
            </CardTitle>
            <div class="text-rui-text-secondary text-body-2">
              {{ t('historical_balances.hint') }}
            </div>
          </div>
          <div class="flex items-center gap-2">
            <RuiButton
              color="primary"
              variant="outlined"
              :disabled="isProcessing || isProcessingTaskRunning"
              @click="triggerHistoricalBalancesProcessing()"
            >
              <template #prepend>
                <RuiProgress
                  v-if="isProcessing && processingProgress"
                  circular
                  :value="processingPercentage"
                  size="24"
                  show-label
                  thickness="2"
                  color="primary"
                />
                <RuiIcon
                  v-else
                  name="lu-refresh-cw"
                  size="16"
                />
              </template>
              <template v-if="isProcessing && processingProgress">
                {{ t('historical_balances.processing_progress', { processed: processingProgress.processed, total: processingProgress.total }) }}
              </template>
              <template v-else>
                {{ t('historical_balances.trigger_processing') }}
              </template>
            </RuiButton>

            <RuiBadge
              color="warning"
              size="sm"
              placement="top"
              offset-x="-4"
              :model-value="!!negativeBalancesCount"
              :text="negativeBalancesCount.toString()"
            >
              <RuiButton
                :disabled="!hasNegativeBalances"
                variant="outlined"
                color="warning"
                @click="showNegativeBalancesDialog = true"
              >
                {{ t('historical_balances.negative_balances.button_label') }}
              </RuiButton>
            </RuiBadge>
          </div>
        </div>
      </template>

      <GetPremiumPlaceholder
        v-if="!premium"
        :title="t('historical_balances.title')"
        :description="t('historical_balances.premium_required')"
      />

      <HistoricalBalancesContent v-else />
    </RuiCard>

    <NegativeBalancesDialog
      v-model="showNegativeBalancesDialog"
      :negative-balances="negativeBalances"
    />
  </TablePageLayout>
</template>
