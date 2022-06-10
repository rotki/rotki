<template>
  <div v-if="actionableItemsLength">
    <v-dialog v-model="mainDialogOpen" max-width="1000">
      <template #activator="{ on }">
        <v-btn color="error" depressed v-on="on">
          <span class="px-2">
            {{ $tc('profit_loss_report.actionable.show_issues') }}
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
<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  ref,
  toRefs
} from '@vue/composition-api';
import { get } from '@vueuse/core';
import ReportActionableCard from '@/components/profitloss/ReportActionableCard.vue';
import { useReports } from '@/store/reports';
import { SelectedReport } from '@/types/reports';

export default defineComponent({
  name: 'ReportActionable',
  components: {
    ReportActionableCard
  },
  props: {
    report: {
      required: true,
      type: Object as PropType<SelectedReport>
    },
    initialOpen: { required: false, type: Boolean, default: false }
  },
  setup(props) {
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

    return {
      mainDialogOpen,
      actionableItemsLength
    };
  }
});
</script>
