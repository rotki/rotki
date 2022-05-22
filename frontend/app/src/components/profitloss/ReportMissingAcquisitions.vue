<template>
  <div>
    <data-table
      ref="tableRef"
      :class="$style.table"
      :headers="headers"
      :items="groupedMissingAcquisitions"
      item-key="asset"
      single-expand
      :expanded.sync="expanded"
      :container="tableContainer"
    >
      <template #item.asset="{ item }">
        <asset-details :asset="item.asset" />
      </template>
      <template #item.time="{ item }">
        <date-display :timestamp="item.startDate" />
        <template v-if="item.startDate !== item.endDate">
          <span>
            {{ $tc('profit_loss_report.actionable.missing_acquisitions.to') }}
            <br />
          </span>
          <date-display :timestamp="item.endDate" />
        </template>
      </template>
      <template #item.total_missing_acquisition="{ item }">
        {{ item.acquisitions.length }}
      </template>
      <template #item.expand="{ item }">
        <row-expander
          :expanded="expanded.includes(item)"
          @click="expanded = expanded.includes(item) ? [] : [item]"
        />
      </template>
      <template #expanded-item="{ item }">
        <table-expand-container visible :colspan="headers.length">
          <data-table
            :headers="childHeaders"
            :items="item.acquisitions"
            :container="tableContainer"
          >
            <template #item.time="{ item: childItem }">
              <date-display :timestamp="childItem.time" />
            </template>
            <template #item.foundAmount="{ item: childItem }">
              <amount-display pnl :value="childItem.foundAmount" />
            </template>
            <template #item.missingAmount="{ item: childItem }">
              <amount-display pnl :value="childItem.missingAmount" />
            </template>
          </data-table>
        </table-expand-container>
      </template>
    </data-table>
    <slot name="actions" />
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
import { DataTableHeader } from 'vuetify';
import RowExpander from '@/components/helper/RowExpander.vue';
import i18n from '@/i18n';
import { MissingAcquisition, SelectedReport } from '@/types/reports';

type GroupedItems = { [asset: string]: MissingAcquisition[] };
type MappedGroupedItems = {
  asset: string;
  startDate: number;
  endDate: number;
  acquisitions: MissingAcquisition[];
};

const headers: DataTableHeader[] = [
  {
    text: i18n
      .t('profit_loss_report.actionable.missing_acquisitions.headers.asset')
      .toString(),
    value: 'asset'
  },
  {
    text: i18n
      .t('profit_loss_report.actionable.missing_acquisitions.headers.time')
      .toString(),
    value: 'time'
  },
  {
    text: i18n
      .t(
        'profit_loss_report.actionable.missing_acquisitions.headers.missing_acquisitions'
      )
      .toString(),
    value: 'total_missing_acquisition',
    sortable: false
  },
  { text: '', value: 'expand', align: 'end', sortable: false }
];

const childHeaders: DataTableHeader[] = [
  {
    text: i18n
      .t('profit_loss_report.actionable.missing_acquisitions.headers.time')
      .toString(),
    value: 'time'
  },
  {
    text: i18n
      .t(
        'profit_loss_report.actionable.missing_acquisitions.headers.found_amount'
      )
      .toString(),
    value: 'foundAmount'
  },
  {
    text: i18n
      .t(
        'profit_loss_report.actionable.missing_acquisitions.headers.missing_amount'
      )
      .toString(),
    value: 'missingAmount'
  }
];

export default defineComponent({
  name: 'ReportMissingAcquisitions',
  components: {
    RowExpander
  },
  props: {
    report: {
      required: true,
      type: Object as PropType<SelectedReport>
    },
    items: { required: true, type: Array as PropType<MissingAcquisition[]> }
  },
  setup(props) {
    const { items } = toRefs(props);
    const groupedMissingAcquisitions = computed<MappedGroupedItems[]>(() => {
      const grouped: GroupedItems = {};

      get(items).forEach((item: MissingAcquisition) => {
        if (grouped[item.asset]) {
          grouped[item.asset].push(item);
        } else {
          grouped[item.asset] = [item];
        }
      });

      return Object.keys(grouped).map(key => {
        const sortedAcquisitions = grouped[key].sort((a, b) => a.time - b.time);
        const startDate = sortedAcquisitions[0].time;
        const endDate = sortedAcquisitions[sortedAcquisitions.length - 1].time;

        return {
          asset: key,
          startDate,
          endDate,
          acquisitions: sortedAcquisitions
        };
      });
    });

    const expanded = ref<MappedGroupedItems[]>([]);

    const tableRef = ref<any>(null);

    const tableContainer = computed(() => {
      return get(tableRef)?.$el;
    });

    return {
      headers,
      childHeaders,
      expanded,
      groupedMissingAcquisitions,
      tableRef,
      tableContainer
    };
  }
});
</script>

<style module lang="scss">
.table {
  scroll-behavior: smooth;
  max-height: calc(100vh - 310px);
  overflow: auto;
}
</style>
