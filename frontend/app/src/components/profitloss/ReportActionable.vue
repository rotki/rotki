<template>
  <div v-if="actionableItemsLength">
    <v-dialog v-model="mainDialogOpen" max-width="1000">
      <template #activator="{ on }">
        <v-btn color="error" depressed v-on="on">
          <span class="pr-2">
            {{ tc('profit_loss_report.actionable.show_issues') }}
          </span>
          <v-chip x-small class="px-2" color="error darken-2">
            {{ actionableItemsLength }}
          </v-chip>
        </v-btn>
      </template>
      <report-actionable-card
        v-if="mainDialogOpen"
        :report="report"
        @set-dialog="mainDialogOpen = $event"
      />
    </v-dialog>
  </div>
</template>
<script setup lang="ts">
import { PropType } from 'vue';
import ReportActionableCard from '@/components/profitloss/ReportActionableCard.vue';
import { useReports } from '@/store/reports';
import { SelectedReport } from '@/types/reports';

const props = defineProps({
  report: {
    required: true,
    type: Object as PropType<SelectedReport>
  },
  initialOpen: { required: false, type: Boolean, default: false }
});

const { initialOpen } = toRefs(props);
const mainDialogOpen = ref<boolean>(get(initialOpen));

const reportsStore = useReports();
const { actionableItems } = toRefs(reportsStore);

const actionableItemsLength = computed(() => {
  let total: number = 0;

  const items = get(actionableItems);

  if (items) {
    total = items.missingAcquisitions.length + items.missingPrices.length;
  }

  return total;
});

const { tc } = useI18n();
</script>
