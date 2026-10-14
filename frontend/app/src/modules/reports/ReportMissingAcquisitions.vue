<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { MissingAcquisition } from '@/modules/reports/report-types';
import { ValueDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useIgnoredAssetOperations } from '@/modules/assets/use-ignored-asset-operations';
import ScrollableDialogContent from '@/modules/core/table/ScrollableDialogContent.vue';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import BadgeDisplay from '@/modules/history/BadgeDisplay.vue';
import { type GroupedMissingAcquisition, groupMissingAcquisitions } from '@/modules/reports/missing-acquisitions';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

const { items, isPinned } = defineProps<{
  items: MissingAcquisition[];
  isPinned: boolean;
}>();

const emit = defineEmits<{
  pin: [];
}>();

defineSlots<{
  actions: () => any;
}>();

const router = useRouter();
const { ignoreAsset } = useIgnoredAssetOperations();
const { isAssetIgnored } = useAssetsStore();

const groupedMissingAcquisitions = computed<GroupedMissingAcquisition[]>(() => groupMissingAcquisitions(items));

const expanded = ref<GroupedMissingAcquisition[]>([]);

const sort = ref<DataTableSortData<GroupedMissingAcquisition>>([]);
const childSort = ref<DataTableSortData<MissingAcquisition>>({
  column: 'time',
  direction: 'asc' as const,
});

const { t } = useI18n({ useScope: 'global' });

const headers = computed<DataTableColumn<GroupedMissingAcquisition>[]>(() => [{
  cellClass: 'py-0! pr-0! pl-3!',
  class: 'py-0! pr-0! pl-3!',
  key: 'expand',
  label: '',
  sortable: false,
}, {
  cellClass: 'py-0',
  key: 'asset',
  label: t('common.asset'),
  sortable: true,
}, ...(isPinned
  ? []
  : [
    {
      cellClass: 'py-2 whitespace-nowrap',
      key: 'startDate',
      label: t('common.datetime'),
      sortable: true,
    },
    {
      align: 'end',
      key: 'total_missing_acquisition',
      label: t('profit_loss_report.actionable.missing_acquisitions.headers.missing_acquisitions'),
      sortable: true,
    },
  ] satisfies DataTableColumn<GroupedMissingAcquisition>[]), {
  align: 'end',
  key: 'total_amount_missing',
  label: t('profit_loss_report.actionable.missing_acquisitions.headers.total_missing'),
}, {
  align: 'end',
  cellClass: isPinned ? 'py-0 px-1!' : 'py-0',
  class: isPinned ? 'w-px px-1!' : 'w-px',
  key: 'action',
  label: '',
}]);

const childHeaders = computed<DataTableColumn<MissingAcquisition>[]>(() => [{
  key: 'time',
  label: t('common.datetime'),
  sortable: true,
}, {
  align: 'end',
  key: 'foundAmount',
  label: t('profit_loss_report.actionable.missing_acquisitions.headers.found_amount'),
  sortable: true,
}, {
  align: 'end',
  key: 'missingAmount',
  label: t('profit_loss_report.actionable.missing_acquisitions.headers.missing_amount'),
  sortable: true,
}, {
  align: 'end',
  key: 'actions',
  label: '',
}]);

useRememberTableSorting<GroupedMissingAcquisition>(TableId.REPORT_MISSING_ACQUISITIONS, sort, headers);
useRememberTableSorting<MissingAcquisition>(TableId.REPORT_MISSING_ACQUISITIONS_DETAIL, childSort, childHeaders);

const isIgnored = (asset: string): boolean => isAssetIgnored(asset);

const [CreateDate, ReuseDate] = createReusableTemplate<{ row: GroupedMissingAcquisition }>();

async function showInHistoryEvent(identifier: number) {
  emit('pin');

  await router.push({
    name: '/history/events/',
    query: {
      missingAcquisitionIdentifier: identifier.toString(),
    },
  });
}
</script>

<template>
  <CreateDate #default="{ row }">
    <DateDisplay
      no-time
      :timestamp="row.startDate"
    />
    <template v-if="row.startDate !== row.endDate">
      <span class="mx-1">{{ t('profit_loss_report.actionable.missing_acquisitions.to') }}</span>
      <DateDisplay
        no-time
        :timestamp="row.endDate"
      />
    </template>
  </CreateDate>
  <ScrollableDialogContent fill>
    <RuiDataTable
      v-model:sort="sort"
      v-model:expanded="expanded"
      :cols="headers"
      :rows="groupedMissingAcquisitions"
      row-attr="asset"
      single-expand
      :dense="isPinned"
      sticky-header
    >
      <template #item.asset="{ row }">
        <AssetDetails
          :asset="row.asset"
          :class="{ 'max-w-44!': isPinned }"
        />
        <div
          v-if="isPinned"
          class="text-xs text-rui-text-secondary whitespace-normal"
        >
          <ReuseDate :row="row" />
        </div>
      </template>
      <template #item.startDate="{ row }">
        <ReuseDate :row="row" />
      </template>
      <template #item.total_missing_acquisition="{ row }">
        {{ row.acquisitions.length }}
      </template>
      <template #item.total_amount_missing="{ row }">
        <ValueDisplay
          class="text-rui-error"
          :value="row.totalAmountMissing"
        />
      </template>
      <template #item.action="{ row }">
        <div class="flex items-center justify-end">
          <RuiTooltip
            v-if="isIgnored(row.asset)"
            :open-delay="400"
          >
            <template #activator>
              <BadgeDisplay
                color="grey"
                class="py-1"
              >
                <RuiIcon
                  size="18"
                  name="lu-eye-off"
                />
              </BadgeDisplay>
            </template>
            {{ t('profit_loss_report.actionable.missing_acquisitions.asset_is_ignored') }}
          </RuiTooltip>
          <RuiTooltip
            v-else
            :open-delay="400"
          >
            <template #activator>
              <RuiButton
                variant="text"
                icon
                size="sm"
                class="text-rui-text-secondary"
                :aria-label="t('assets.action.ignore')"
                data-testid="missing-acquisition-ignore"
                @click="ignoreAsset(row.asset)"
              >
                <RuiIcon
                  size="18"
                  name="lu-eye-off"
                />
              </RuiButton>
            </template>
            {{ t('assets.action.ignore') }}
          </RuiTooltip>
        </div>
      </template>
      <template #expanded-item="{ row }">
        <RuiDataTable
          v-model:sort="childSort"
          :cols="childHeaders"
          :rows="row.acquisitions"
          :class="{ 'my-2': isPinned }"
          outlined
          dense
          row-attr="asset"
        >
          <template #item.time="{ row: childItem }">
            <DateDisplay :timestamp="childItem.time" />
          </template>
          <template #item.foundAmount="{ row: childItem }">
            <ValueDisplay
              :value="childItem.foundAmount"
              pnl
            />
          </template>
          <template #item.missingAmount="{ row: childItem }">
            <ValueDisplay
              class="text-rui-error"
              :value="childItem.missingAmount"
            />
          </template>
          <template #item.actions="{ row: childItem }">
            <RuiButton
              v-if="childItem.originatingEventId"
              variant="text"
              color="primary"
              @click="showInHistoryEvent(childItem.originatingEventId)"
            >
              {{ t('profit_loss_report.actionable.missing_acquisitions.show_in_history_event') }}
              <template #append>
                <RuiIcon name="lu-chevron-right" />
              </template>
            </RuiButton>
          </template>
        </RuiDataTable>
      </template>
    </RuiDataTable>
    <template #footer>
      <slot name="actions" />
    </template>
  </ScrollableDialogContent>
</template>
