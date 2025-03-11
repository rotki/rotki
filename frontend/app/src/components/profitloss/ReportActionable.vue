<script setup lang="ts">
import type { Report } from '@/types/reports';
import ReportActionableCard from '@/components/profitloss/ReportActionableCard.vue';
import { useReportsStore } from '@/store/reports';

const props = withDefaults(
  defineProps<{
    report: Report;
    initialOpen?: boolean;
  }>(),
  {
    initialOpen: false,
  },
);

const emit = defineEmits<{
  (e: 'regenerate'): void;
}>();

function regenerateReport() {
  emit('regenerate');
}

const { initialOpen, report } = toRefs(props);
const mainDialogOpen = ref<boolean>(get(initialOpen));

const reportsStore = useReportsStore();
const { actionableItems } = toRefs(reportsStore);

const actionableItemsLength = computed(() => {
  let total = 0;

  const items = get(actionableItems);

  if (items)
    total = items.missingAcquisitions.length + items.missingPrices.length;

  return total;
});

const { t } = useI18n();
</script>

<template>
  <div
    v-if="actionableItemsLength"
    class="flex"
  >
    <RuiDialog
      v-model="mainDialogOpen"
      max-width="1000"
    >
      <template #activator="{ attrs }">
        <RuiButton
          color="error"
          v-bind="attrs"
        >
          <span class="pr-2">
            {{ t('profit_loss_report.actionable.show_issues') }}
          </span>
          <template #append>
            <RuiChip
              size="sm"
              color="error"
              class="!p-0 !bg-rui-error-darker"
            >
              {{ actionableItemsLength.toString() }}
            </RuiChip>
          </template>
        </RuiButton>
      </template>
      <ReportActionableCard
        v-if="mainDialogOpen"
        :report="report"
        @set-dialog="mainDialogOpen = $event"
        @regenerate="regenerateReport()"
      />
    </RuiDialog>
  </div>
</template>
