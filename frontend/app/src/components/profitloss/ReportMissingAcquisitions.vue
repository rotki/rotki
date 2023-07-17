<script setup lang="ts">
import { type PropType, type Ref } from 'vue';
import { type DataTableHeader } from '@/types/vuetify';
import { type MissingAcquisition, type SelectedReport } from '@/types/reports';
import { type LedgerAction } from '@/types/history/ledger-action/ledger-actions';

type GroupedItems = Record<string, MissingAcquisition[]>;

interface MappedGroupedItems {
  asset: string;
  startDate: number;
  endDate: number;
  acquisitions: MissingAcquisition[];
}

const props = defineProps({
  report: {
    required: true,
    type: Object as PropType<SelectedReport>
  },
  items: { required: true, type: Array as PropType<MissingAcquisition[]> },
  isPinned: { required: true, type: Boolean, default: false }
});

const { items, isPinned } = toRefs(props);

const { isAssetIgnored, ignoreAsset } = useIgnoredAssetsStore();

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

const tableContainer = computed(() => get(tableRef)?.$el);

const { t } = useI18n();

const headers = computed<DataTableHeader[]>(() => {
  const pinnedClass = get(isPinned) ? { class: 'px-2', cellClass: 'px-2' } : {};

  return [
    {
      text: t('common.asset').toString(),
      value: 'asset',
      ...pinnedClass
    },
    {
      text: t('common.datetime').toString(),
      value: 'startDate',
      ...pinnedClass
    },
    {
      text: t(
        'profit_loss_report.actionable.missing_acquisitions.headers.missing_acquisitions'
      ).toString(),
      value: 'total_missing_acquisition',
      sortable: false,
      ...pinnedClass
    },
    {
      text: t(
        'profit_loss_report.actionable.missing_acquisitions.headers.quick_action'
      ).toString(),
      value: 'action',
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

const childHeaders = computed<DataTableHeader[]>(() => {
  const pinnedClass = get(isPinned) ? { class: 'px-2', cellClass: 'px-2' } : {};

  return [
    {
      text: t('common.datetime').toString(),
      value: 'time',
      ...pinnedClass
    },
    {
      text: t(
        'profit_loss_report.actionable.missing_acquisitions.headers.found_amount'
      ).toString(),
      value: 'foundAmount',
      ...pinnedClass
    },
    {
      text: t(
        'profit_loss_report.actionable.missing_acquisitions.headers.missing_amount'
      ).toString(),
      value: 'missingAmount',
      ...pinnedClass
    },
    {
      text: t(
        'profit_loss_report.actionable.missing_acquisitions.headers.quick_action'
      ).toString(),
      value: 'action',
      sortable: false,
      ...pinnedClass
    }
  ];
});

const { setOpenDialog } = useLedgerActionsForm();

const ledgerActionForm: Ref<Partial<LedgerAction> | null> = ref(null);
const addLedgerAction = (item: MissingAcquisition) => {
  const form = {
    timestamp: item.time,
    amount: item.missingAmount,
    asset: item.asset
  };

  set(ledgerActionForm, form);
  setOpenDialog(true);
};

const isIgnored = (asset: string) => get(isAssetIgnored(asset));
</script>

<template>
  <div>
    <DataTable
      ref="tableRef"
      class="table-inside-dialog"
      :class="{
        [$style['table--pinned']]: isPinned
      }"
      :headers="headers"
      :items="groupedMissingAcquisitions"
      item-key="asset"
      single-expand
      :expanded.sync="expanded"
      :container="tableContainer"
      :dense="isPinned"
      multi-sort
      :must-sort="false"
    >
      <template #item.asset="{ item }">
        <AssetDetails :asset="item.asset" link />
      </template>
      <template #item.startDate="{ item }">
        <DateDisplay :timestamp="item.startDate" />
        <template v-if="item.startDate !== item.endDate">
          <span>
            {{ t('profit_loss_report.actionable.missing_acquisitions.to') }}
            <br />
          </span>
          <DateDisplay :timestamp="item.endDate" />
        </template>
      </template>
      <template #item.total_missing_acquisition="{ item }">
        {{ item.acquisitions.length }}
      </template>
      <template #item.action="{ item }">
        <VMenu offset-y>
          <template #activator="{ on }">
            <VBtn icon v-on="on">
              <VIcon>mdi-dots-vertical</VIcon>
            </VBtn>
          </template>
          <VList>
            <VListItem link @click="ignoreAsset(item.asset)">
              <VListItemTitle>{{ t('assets.ignore') }}</VListItemTitle>
            </VListItem>
          </VList>
        </VMenu>

        <VTooltip v-if="isIgnored(item.asset)" bottom>
          <template #activator="{ on }">
            <BadgeDisplay class="ml-2" color="grey" v-on="on">
              <VIcon small> mdi-eye-off </VIcon>
            </BadgeDisplay>
          </template>
          <span>
            {{
              t(
                'profit_loss_report.actionable.missing_acquisitions.asset_is_ignored'
              )
            }}
          </span>
        </VTooltip>
      </template>
      <template #item.expand="{ item }">
        <RowExpander
          :expanded="expanded.includes(item)"
          @click="expanded = expanded.includes(item) ? [] : [item]"
        />
      </template>
      <template #expanded-item="{ item }">
        <TableExpandContainer visible :colspan="headers.length">
          <DataTable
            :headers="childHeaders"
            :items="item.acquisitions"
            :container="tableContainer"
          >
            <template #item.time="{ item: childItem }">
              <DateDisplay :timestamp="childItem.time" />
            </template>
            <template #item.foundAmount="{ item: childItem }">
              <AmountDisplay pnl :value="childItem.foundAmount" />
            </template>
            <template #item.missingAmount="{ item: childItem }">
              <AmountDisplay pnl :value="childItem.missingAmount" />
            </template>
            <template #item.action="{ item: childItem }">
              <VMenu offset-y>
                <template #activator="{ on }">
                  <VBtn icon v-on="on">
                    <VIcon>mdi-dots-vertical</VIcon>
                  </VBtn>
                </template>
                <VList>
                  <VListItem link @click="addLedgerAction(childItem)">
                    <VListItemTitle>
                      {{
                        t(
                          'profit_loss_report.actionable.missing_acquisitions.add_ledger_action'
                        )
                      }}
                    </VListItemTitle>
                  </VListItem>
                </VList>
              </VMenu>
            </template>
          </DataTable>
        </TableExpandContainer>
      </template>
    </DataTable>
    <slot name="actions" />

    <LedgerActionFormDialog :editable-item="ledgerActionForm" />
  </div>
</template>

<style module lang="scss">
.table {
  &--pinned {
    max-height: 100%;
    height: calc(100vh - 230px);
  }
}
</style>
