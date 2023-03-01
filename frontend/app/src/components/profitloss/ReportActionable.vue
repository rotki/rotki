<script setup lang="ts">
import { type PropType } from 'vue';
import { type SelectedReport } from '@/types/reports';
import { Routes } from '@/router/routes';

const props = defineProps({
  report: {
    required: true,
    type: Object as PropType<SelectedReport>
  },
  initialOpen: { required: false, type: Boolean, default: false }
});

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

const { tc } = useI18n();

const router = useRouter();
const regenerateReport = async () => {
  await router.push({
    path: Routes.PROFIT_LOSS_REPORTS,
    query: {
      regenerate: 'true',
      start: get(report).start.toString(),
      end: get(report).end.toString()
    }
  });
};
</script>
<template>
  <div v-if="actionableItemsLength" class="d-flex">
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
        @regenerate="regenerateReport"
      />
    </v-dialog>

    <div>
      <v-btn text class="ml-2" @click="regenerateReport">
        <v-icon class="mr-2">mdi-refresh</v-icon>
        {{ tc('profit_loss_report.actionable.actions.regenerate_report') }}
      </v-btn>
    </div>
  </div>
</template>
