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
    <data-table
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
        <asset-details :asset="item.asset" link />
      </template>
      <template #item.startDate="{ item }">
        <date-display :timestamp="item.startDate" />
        <template v-if="item.startDate !== item.endDate">
          <span>
            {{ t('profit_loss_report.actionable.missing_acquisitions.to') }}
            <br />
          </span>
          <date-display :timestamp="item.endDate" />
        </template>
      </template>
      <template #item.total_missing_acquisition="{ item }">
        {{ item.acquisitions.length }}
      </template>
      <template #item.action="{ item }">
        <v-menu offset-y>
          <template #activator="{ on }">
            <v-btn icon v-on="on">
              <v-icon>mdi-dots-vertical</v-icon>
            </v-btn>
          </template>
          <v-list>
            <v-list-item link @click="ignoreAsset(item.asset)">
              <v-list-item-title>{{ t('assets.ignore') }}</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>

        <v-tooltip v-if="isIgnored(item.asset)" bottom>
          <template #activator="{ on }">
            <badge-display class="ml-2" color="grey" v-on="on">
              <v-icon small> mdi-eye-off </v-icon>
            </badge-display>
          </template>
          <span>
            {{
              t(
                'profit_loss_report.actionable.missing_acquisitions.asset_is_ignored'
              )
            }}
          </span>
        </v-tooltip>
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
            <template #item.action="{ item: childItem }">
              <v-menu offset-y>
                <template #activator="{ on }">
                  <v-btn icon v-on="on">
                    <v-icon>mdi-dots-vertical</v-icon>
                  </v-btn>
                </template>
                <v-list>
                  <v-list-item link @click="addLedgerAction(childItem)">
                    <v-list-item-title>
                      {{
                        t(
                          'profit_loss_report.actionable.missing_acquisitions.add_ledger_action'
                        )
                      }}
                    </v-list-item-title>
                  </v-list-item>
                </v-list>
              </v-menu>
            </template>
          </data-table>
        </table-expand-container>
      </template>
    </data-table>
    <slot name="actions" />

    <ledger-action-form-dialog :editable-item="ledgerActionForm" />
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
