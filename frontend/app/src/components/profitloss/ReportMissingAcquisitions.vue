<template>
  <div>
    <data-table
      ref="tableRef"
      :class="{
        [$style.table]: true,
        [$style['table--pinned']]: isPinned
      }"
      :headers="headers"
      :items="groupedMissingAcquisitions"
      item-key="asset"
      single-expand
      :expanded.sync="expanded"
      :container="tableContainer"
      :dense="isPinned"
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
import { get } from '@vueuse/core';
import { computed, defineComponent, PropType, Ref, ref, toRefs } from 'vue';
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

const headers = (isPinned: Ref<boolean>) => {
  return computed<DataTableHeader[]>(() => {
    const pinnedClass = get(isPinned)
      ? { class: 'px-2', cellClass: 'px-2' }
      : {};

    return [
      {
        text: i18n
          .t('profit_loss_report.actionable.missing_acquisitions.headers.asset')
          .toString(),
        value: 'asset',
        ...pinnedClass
      },
      {
        text: i18n
          .t('profit_loss_report.actionable.missing_acquisitions.headers.time')
          .toString(),
        value: 'time',
        ...pinnedClass
      },
      {
        text: i18n
          .t(
            'profit_loss_report.actionable.missing_acquisitions.headers.missing_acquisitions'
          )
          .toString(),
        value: 'total_missing_acquisition',
        sortable: false,
        ...pinnedClass
      },
      {
        text: '',
        value: 'expand',
        align: 'end',
        sortable: false,
        ...pinnedClass
      }
    ];
  });
};

const childHeaders = (isPinned: Ref<boolean>) => {
  return computed<DataTableHeader[]>(() => {
    const pinnedClass = get(isPinned)
      ? { class: 'px-2', cellClass: 'px-2' }
      : {};

    return [
      {
        text: i18n
          .t('profit_loss_report.actionable.missing_acquisitions.headers.time')
          .toString(),
        value: 'time',
        ...pinnedClass
      },
      {
        text: i18n
          .t(
            'profit_loss_report.actionable.missing_acquisitions.headers.found_amount'
          )
          .toString(),
        value: 'foundAmount',
        ...pinnedClass
      },
      {
        text: i18n
          .t(
            'profit_loss_report.actionable.missing_acquisitions.headers.missing_amount'
          )
          .toString(),
        value: 'missingAmount',
        ...pinnedClass
      }
    ];
  });
};

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
    items: { required: true, type: Array as PropType<MissingAcquisition[]> },
    isPinned: { required: true, type: Boolean, default: false }
  },
  setup(props) {
    const { items, isPinned } = toRefs(props);

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
      headers: headers(isPinned),
      childHeaders: childHeaders(isPinned),
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

  &--pinned {
    max-height: 100%;
    height: calc(100vh - 230px);
  }
}
</style>
