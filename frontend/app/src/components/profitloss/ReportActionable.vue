<script setup lang="ts">
import { type SelectedReport } from '@/types/reports';

const props = withDefaults(
  defineProps<{
    report: SelectedReport;
    initialOpen?: boolean;
  }>(),
  {
    initialOpen: false
  }
);

const emit = defineEmits<{
  (e: 'regenerate'): void;
}>();

const regenerateReport = () => {
  emit('regenerate');
};

const { initialOpen, report } = toRefs(props);
const mainDialogOpen = ref<boolean>(get(initialOpen));

const reportsStore = useReportsStore();
const { actionableItems } = toRefs(reportsStore);

const actionableItemsLength = computed(() => {
  let total = 0;

  const items = get(actionableItems);

  if (items) {
    total = items.missingAcquisitions.length + items.missingPrices.length;
  }

  return total;
});

const { t } = useI18n();
</script>

<template>
  <div v-if="actionableItemsLength" class="flex">
    <VDialog v-model="mainDialogOpen" max-width="1000">
      <template #activator="{ on }">
        <RuiButton color="error" v-on="on">
          <span class="pr-2">
            {{ t('profit_loss_report.actionable.show_issues') }}
          </span>
          <template #append>
            <RuiChip
              size="sm"
              class="!text-white !p-0 !bg-rui-error-darker"
              :label="actionableItemsLength"
            />
          </template>
        </RuiButton>
      </template>
      <ReportActionableCard
        v-if="mainDialogOpen"
        :report="report"
        @set-dialog="mainDialogOpen = $event"
        @regenerate="regenerateReport()"
      />
    </VDialog>
  </div>
</template>
