<script setup lang="ts">
import { type DataTableHeader } from '@/types/vuetify';
import { type ProfitLossEvents, type SelectedReport } from '@/types/reports';
import { isTransactionEvent } from '@/utils/report';

const props = withDefaults(
  defineProps<{
    report: SelectedReport;
    loading?: boolean;
    refreshing?: boolean;
  }>(),
  {
    loading: false,
    refreshing: false
  }
);

const emit = defineEmits<{
  (
    e: 'update:page',
    page: { reportId: number; offset: number; limit: number }
  ): void;
}>();

const { t } = useI18n();

interface PaginationOptions {
  page: number;
  itemsPerPage: number;
  sortBy: any[];
  sortDesc: boolean[];
}

const { report } = toRefs(props);

const options = ref<PaginationOptions | null>(null);

const route = useRoute();
const { getChain } = useSupportedChains();

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: '',
    value: 'group',
    sortable: false,
    class: 'px-0',
    cellClass: 'px-0'
  },
  {
    text: t('common.type'),
    align: 'center',
    value: 'type',
    width: 110,
    sortable: false
  },
  {
    text: t('common.location'),
    value: 'location',
    width: '120px',
    align: 'center',
    cellClass: 'py-2',
    sortable: false
  },
  {
    text: t('profit_loss_events.headers.tax_free_amount'),
    align: 'end',
    value: 'free_amount',
    sortable: false
  },
  {
    text: t('profit_loss_events.headers.taxable_amount'),
    align: 'end',
    value: 'taxable_amount',
    sortable: false
  },
  {
    text: t('common.price'),
    align: 'end',
    value: 'price',
    sortable: false
  },
  {
    text: t('profit_loss_events.headers.pnl_free'),
    align: 'end',
    value: 'pnl_free',
    sortable: false
  },
  {
    text: t('profit_loss_events.headers.pnl_taxable'),
    align: 'end',
    value: 'pnl_taxable',
    sortable: false
  },
  {
    text: t('common.datetime'),
    value: 'time',
    sortable: false
  },
  {
    text: t('profit_loss_events.headers.notes'),
    value: 'notes',
    sortable: false
  },
  {
    text: t('common.actions_text'),
    value: 'actions',
    align: 'end',
    width: 140,
    sortable: false
  }
]);

const items = computed(() => {
  const entries = report.value.entries.map((value, index) => ({
    ...value,
    id: index
  }));

  return entries.map((entry, index) => ({
    ...entry,
    groupLine: checkGroupLine(entries, index)
  }));
});

const itemLength = computed(() => {
  const { entriesFound, entriesLimit } = report.value;
  if (entriesLimit > 0 && entriesLimit <= entriesFound) {
    return entriesLimit;
  }
  return entriesFound;
});

const premium = usePremium();

const showUpgradeMessage = computed(
  () =>
    !premium.value && report.value.totalActions > report.value.processedActions
);

const updatePagination = async (options: PaginationOptions | null) => {
  if (!options) {
    return;
  }
  const { itemsPerPage, page } = options;

  const reportId = Number.parseInt(get(route).params.id as string);

  emit('update:page', {
    reportId,
    limit: itemsPerPage,
    offset: itemsPerPage * (page - 1)
  });
};

watch(options, updatePagination);

const checkGroupLine = (entries: ProfitLossEvents, index: number) => {
  const current = entries[index];
  const prev = index - 1 >= 0 ? entries[index - 1] : null;
  const next = index + 1 < entries.length ? entries[index + 1] : null;

  return {
    top: !!(current?.groupId && prev && current?.groupId === prev?.groupId),
    bottom: !!(current?.groupId && next && current?.groupId === next?.groupId)
  };
};

const css = useCssModule();
</script>

<template>
  <RuiCard>
    <template #header>{{ t('common.events') }}</template>
    <DataTable
      :headers="tableHeaders"
      :items="items"
      single-expand
      :loading="loading || refreshing"
      :expanded="items"
      :server-items-length="itemLength"
      :options.sync="options"
      sort-by="time"
    >
      <template #item.group="{ item }">
        <RuiTooltip
          v-if="item.groupId && (item.groupLine.top || item.groupLine.bottom)"
          :popper="{ placement: 'right' }"
          open-delay="400"
          class="h-full"
        >
          <template #activator>
            <div :class="css.group">
              <div
                v-if="item.groupLine.top"
                :class="[css.group__line, css['group__line-top']]"
              />
              <div :class="css.group__dot" />
              <div
                v-if="item.groupLine.bottom"
                :class="[css.group__line, css['group__line-bottom']]"
              />
            </div>
          </template>
          <span>{{ t('profit_loss_events.same_action') }}</span>
        </RuiTooltip>
      </template>
      <template #item.type="{ item }">
        <ProfitLossEventType :type="item.type" />
      </template>
      <template #item.location="{ item }">
        <LocationDisplay :identifier="item.location" />
      </template>
      <template #item.time="{ item }">
        <DateDisplay :timestamp="item.timestamp" />
      </template>
      <template #item.free_amount="{ item }">
        <div class="flex items-center justify-between flex-nowrap gap-2">
          <AssetLink
            v-if="item.asset"
            icon
            :asset="item.asset"
            class="mr-2"
            link
          >
            <AssetIcon :identifier="item.asset" size="24px" />
          </AssetLink>
          <AmountDisplay
            force-currency
            :value="item.freeAmount"
            :asset="item.asset ? item.asset : ''"
          />
        </div>
      </template>
      <template #item.taxable_amount="{ item }">
        <AmountDisplay
          force-currency
          :value="item.taxableAmount"
          :asset="item.asset ? item.asset : ''"
        />
      </template>
      <template #item.price="{ item }">
        <AmountDisplay
          force-currency
          :value="item.price"
          show-currency="symbol"
          :fiat-currency="report.settings.profitCurrency"
        />
      </template>
      <template #item.pnl_taxable="{ item }">
        <AmountDisplay
          pnl
          force-currency
          :value="item.pnlTaxable"
          show-currency="symbol"
          :fiat-currency="report.settings.profitCurrency"
        />
      </template>
      <template #item.pnl_free="{ item }">
        <AmountDisplay
          pnl
          force-currency
          :value="item.pnlFree"
          show-currency="symbol"
          :fiat-currency="report.settings.profitCurrency"
        />
      </template>
      <template v-if="showUpgradeMessage" #body.prepend="{ headers }">
        <UpgradeRow
          events
          :total="report.totalActions"
          :limit="report.processedActions"
          :time-end="report.lastProcessedTimestamp"
          :time-start="report.firstProcessedTimestamp"
          :colspan="headers.length"
          :label="t('common.events')"
        />
      </template>
      <template #item.notes="{ item }">
        <div class="py-4">
          <HistoryEventNote
            v-if="isTransactionEvent(item)"
            :notes="item.notes"
            :amount="
              item.taxableAmount.isZero() ? item.freeAmount : item.taxableAmount
            "
            :asset="item.asset"
            :chain="getChain(item.location)"
          />
          <template v-else>{{ item.notes }}</template>
        </div>
      </template>
      <template #item.actions="{ item }">
        <ReportProfitLossEventAction
          :event="item"
          :currency="report.settings.profitCurrency"
        />
      </template>
      <template #expanded-item="{ headers, item }">
        <CostBasisTable
          v-if="item.costBasis"
          :show-group-line="item.groupLine.bottom"
          :currency="report.settings.profitCurrency"
          :colspan="headers.length"
          :cost-basis="item.costBasis"
        />
      </template>
    </DataTable>
  </RuiCard>
</template>

<style module lang="scss">
.group {
  height: 100%;
  position: relative;
  width: 10px;
  margin-left: 1.5rem;

  &__dot {
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 10px;
    height: 10px;
    border-radius: 10px;
    background: var(--v-primary-base);
  }

  &__line {
    position: absolute;
    height: 50%;
    left: 50%;
    width: 0;
    transform: translateX(-50%);
    border-left: 2px dashed var(--v-primary-base);

    &-top {
      top: 0;
    }

    &-bottom {
      bottom: 0;
    }
  }
}
</style>
