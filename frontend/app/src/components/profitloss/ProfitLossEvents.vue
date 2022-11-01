<template>
  <card outlined-body>
    <template #title>{{ tc('common.events') }}</template>
    <data-table
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
        <v-tooltip v-if="item.groupId" right>
          <template #activator="{ on, attrs }">
            <div v-bind="attrs" :class="$style['group']" v-on="on">
              <div
                v-if="item.groupLine.top"
                :class="`${$style['group__line']} ${$style['group__line-top']}`"
              />
              <div :class="$style['group__dot']" />
              <div
                v-if="item.groupLine.bottom"
                :class="`${$style['group__line']} ${$style['group__line-bottom']}`"
              />
            </div>
          </template>
          <span>{{ tc('profit_loss_events.same_action') }}</span>
        </v-tooltip>
      </template>
      <template #item.type="{ item }">
        <profit-loss-event-type :type="item.type" />
      </template>
      <template #item.location="{ item }">
        <location-display :identifier="item.location" />
      </template>
      <template #item.time="{ item }">
        <date-display :timestamp="item.timestamp" />
      </template>
      <template #item.free_amount="{ item }">
        <v-row no-gutters align="center" class="flex-nowrap">
          <v-col v-if="item.asset" cols="auto">
            <asset-link icon :asset="item.asset" class="mr-2">
              <asset-icon :identifier="item.asset" size="24px" />
            </asset-link>
          </v-col>
          <v-col>
            <div>
              <amount-display
                force-currency
                :value="item.freeAmount"
                :asset="item.asset ? item.asset : ''"
              />
            </div>
          </v-col>
        </v-row>
      </template>
      <template #item.taxable_amount="{ item }">
        <amount-display
          force-currency
          :value="item.taxableAmount"
          :asset="item.asset ? item.asset : ''"
        />
      </template>
      <template #item.price="{ item }">
        <amount-display
          force-currency
          :value="item.price"
          :fiat-currency="report.settings.profitCurrency"
        />
      </template>
      <template #item.pnl_taxable="{ item }">
        <amount-display
          pnl
          force-currency
          :value="item.pnlTaxable"
          :fiat-currency="report.settings.profitCurrency"
        />
      </template>
      <template #item.pnl_free="{ item }">
        <amount-display
          pnl
          force-currency
          :value="item.pnlFree"
          :fiat-currency="report.settings.profitCurrency"
        />
      </template>
      <template v-if="showUpgradeMessage" #body.prepend="{ headers }">
        <upgrade-row
          events
          :total="report.totalActions"
          :limit="report.processedActions"
          :time-end="report.lastProcessedTimestamp"
          :time-start="report.firstProcessedTimestamp"
          :colspan="headers.length"
          :label="tc('common.events')"
        />
      </template>
      <template #item.notes="{ item }">
        <div class="py-4">
          <transaction-event-note
            v-if="isTransactionEvent(item)"
            :notes="item.notes"
            :amount="
              item.taxableAmount.isZero() ? item.freeAmount : item.taxableAmount
            "
            :asset="item.asset"
          />
          <template v-else>{{ item.notes }}</template>
        </div>
      </template>
      <template #expanded-item="{ headers, item }">
        <cost-basis-table
          v-if="item.costBasis"
          :show-group-line="item.groupLine.bottom"
          :currency="report.settings.profitCurrency"
          :colspan="headers.length"
          :cost-basis="item.costBasis"
        />
      </template>
    </data-table>
  </card>
</template>

<script setup lang="ts">
import { PropType } from 'vue';
import { DataTableHeader } from 'vuetify';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import DataTable from '@/components/helper/DataTable.vue';
import TransactionEventNote from '@/components/history/transactions/TransactionEventNote.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import CostBasisTable from '@/components/profitloss/CostBasisTable.vue';
import ProfitLossEventType from '@/components/profitloss/ProfitLossEventType.vue';
import { usePremium } from '@/composables/premium';
import {
  ProfitLossEvent,
  ProfitLossEvents,
  ProfitLossEventTypeEnum,
  SelectedReport
} from '@/types/reports';

type PaginationOptions = {
  page: number;
  itemsPerPage: number;
  sortBy: any[];
  sortDesc: boolean[];
};

const props = defineProps({
  loading: {
    required: false,
    type: Boolean,
    default: false
  },
  refreshing: {
    required: false,
    type: Boolean,
    default: false
  },
  report: {
    required: true,
    type: Object as PropType<SelectedReport>
  }
});

const emit = defineEmits<{
  (
    e: 'update:page',
    page: { reportId: number; offset: number; limit: number }
  ): void;
}>();

const route = useRoute();
const options = ref<PaginationOptions | null>(null);
const { report } = toRefs(props);

const { tc } = useI18n();

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: '',
    value: 'group',
    sortable: false,
    class: 'px-0',
    cellClass: 'px-0'
  },
  {
    text: tc('common.type'),
    align: 'center',
    value: 'type',
    width: 110,
    sortable: false
  },
  {
    text: tc('common.location'),
    value: 'location',
    width: '120px',
    align: 'center',
    sortable: false
  },
  {
    text: tc('profit_loss_events.headers.tax_free_amount'),
    align: 'end',
    value: 'free_amount',
    sortable: false
  },
  {
    text: tc('profit_loss_events.headers.taxable_amount'),
    align: 'end',
    value: 'taxable_amount',
    sortable: false
  },
  {
    text: tc('common.price'),
    align: 'end',
    value: 'price',
    sortable: false
  },
  {
    text: tc('profit_loss_events.headers.pnl_free'),
    align: 'end',
    value: 'pnl_free',
    sortable: false
  },
  {
    text: tc('profit_loss_events.headers.pnl_taxable'),
    align: 'end',
    value: 'pnl_taxable',
    sortable: false
  },
  {
    text: tc('common.datetime'),
    value: 'time',
    sortable: false
  },
  {
    text: tc('profit_loss_events.headers.notes'),
    value: 'notes',
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

  const reportId = parseInt(get(route).params.id as string);

  emit('update:page', {
    reportId,
    limit: itemsPerPage,
    offset: itemsPerPage * (page - 1)
  });
};

const isTransactionEvent = (item: ProfitLossEvent) => {
  return item.type === ProfitLossEventTypeEnum.TRANSACTION_EVENT;
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
</script>
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
