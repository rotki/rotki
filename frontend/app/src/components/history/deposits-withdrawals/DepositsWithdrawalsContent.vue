<script setup lang="ts">
import { Routes } from '@/router/routes';
import { Section } from '@/types/status';
import { IgnoreActionType } from '@/types/history/ignored';
import { SavedFilterLocation } from '@/types/filtering';
import type {
  AssetMovement,
  AssetMovementEntry,
  AssetMovementRequestPayload,
} from '@/types/history/asset-movements';
import type { Collection } from '@/types/collection';
import type { Filters, Matcher } from '@/composables/filters/asset-movement';
import type { Writeable } from '@/types';
import type { DataTableColumn } from '@rotki/ui-library-compat';

const props = withDefaults(
  defineProps<{
    locationOverview?: string;
  }>(),
  {
    locationOverview: '',
  },
);

const { t } = useI18n();

const { locationOverview } = toRefs(props);

const showIgnoredAssets: Ref<boolean> = ref(false);

const mainPage = computed(() => get(locationOverview) === '');

const tableHeaders = computed<DataTableColumn[]>(() => {
  const overview = !get(mainPage);
  const headers: DataTableColumn[] = [
    {
      label: '',
      key: 'ignoredInAccounting',
      class: !overview ? '!p-0' : '',
      cellClass: !overview ? '!p-0' : '!w-0 !max-w-[4rem]',
    },
    {
      label: t('common.location'),
      key: 'location',
      class: '!w-[7.5rem]',
      cellClass: '!py-1',
      align: 'center',
      sortable: true,
    },
    {
      label: t('deposits_withdrawals.headers.action'),
      key: 'category',
      align: overview ? 'start' : 'center',
      class: `text-no-wrap${overview ? ' !pl-0' : ''}`,
      cellClass: overview ? '!pl-0' : 'py-1',
      sortable: true,
    },
    {
      label: t('common.asset'),
      cellClass: '!py-1',
      key: 'asset',
    },
    {
      label: t('common.amount'),
      key: 'amount',
      align: 'end',
      sortable: true,
    },
    {
      label: t('deposits_withdrawals.headers.fee'),
      key: 'fee',
      align: 'end',
      sortable: true,
    },
    {
      label: t('common.datetime'),
      key: 'timestamp',
      sortable: true,
    },
  ];

  if (overview)
    headers.splice(1, 1);

  return headers;
});

const extraParams = computed(() => ({
  excludeIgnoredAssets: !get(showIgnoredAssets),
}));

const { fetchAssetMovements, refreshAssetMovements } = useAssetMovements();

const {
  selected,
  expanded,
  isLoading,
  state: assetMovements,
  filters,
  matchers,
  setPage,
  sort,
  pagination,
  setFilter,
  fetchData,
} = usePaginationFilters<
  AssetMovement,
  AssetMovementRequestPayload,
  AssetMovementEntry,
  Collection<AssetMovementEntry>,
  Filters,
  Matcher
>(locationOverview, mainPage, useAssetMovementFilters, fetchAssetMovements, {
  onUpdateFilters(query) {
    set(showIgnoredAssets, query.excludeIgnoredAssets === 'false');
  },
  customPageParams: computed<Partial<AssetMovementRequestPayload>>(() => {
    const params: Writeable<Partial<AssetMovementRequestPayload>> = {};
    const location = get(locationOverview);

    if (location)
      params.location = toSnakeCase(location);

    return params;
  }),
  extraParams,
});

useHistoryAutoRefresh(fetchData);

const { ignore } = useIgnore(
  {
    actionType: IgnoreActionType.MOVEMENTS,
    toData: (item: AssetMovementEntry) => item.identifier,
  },
  selected,
  () => fetchData(),
);

const { isLoading: isSectionLoading } = useStatusStore();
const loading = isSectionLoading(Section.ASSET_MOVEMENT);

const value = computed({
  get: () => {
    if (!get(mainPage))
      return undefined;

    return get(selected).map(({ identifier }: AssetMovementEntry) => identifier);
  },
  set: (values) => {
    set(selected, get(assetMovements).data.filter(({ identifier }: AssetMovementEntry) => values?.includes(identifier)));
  },
});

function getItemClass(item: AssetMovementEntry) {
  return item.ignoredInAccounting ? 'opacity-50' : '';
}

const pageRoute = Routes.HISTORY_DEPOSITS_WITHDRAWALS;

onMounted(async () => {
  await fetchData();
  await refreshAssetMovements();
});

watch(loading, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading)
    await fetchData();
});
</script>

<template>
  <TablePageLayout
    :hide-header="!mainPage"
    :child="!mainPage"
    :title="[t('navigation_menu.history'), t('deposits_withdrawals.title')]"
  >
    <template #buttons>
      <RuiTooltip :open-delay="400">
        <template #activator>
          <RuiButton
            variant="outlined"
            color="primary"
            :loading="loading"
            @click="refreshAssetMovements(true)"
          >
            <template #prepend>
              <RuiIcon name="refresh-line" />
            </template>
            {{ t('common.refresh') }}
          </RuiButton>
        </template>
        {{ t('deposits_withdrawals.refresh_tooltip') }}
      </RuiTooltip>
    </template>

    <RuiCard>
      <template
        v-if="!mainPage"
        #header
      >
        <CardTitle>
          <NavigatorLink :to="{ path: pageRoute }">
            {{ t('deposits_withdrawals.title') }}
          </NavigatorLink>
        </CardTitle>
      </template>

      <HistoryTableActions v-if="mainPage">
        <template #filter>
          <TableStatusFilter>
            <div class="py-1 max-w-[16rem]">
              <RuiSwitch
                v-model="showIgnoredAssets"
                class="p-4"
                color="primary"
                hide-details
                :label="t('transactions.filter.show_ignored_assets')"
              />
            </div>
          </TableStatusFilter>
          <TableFilter
            class="min-w-full sm:min-w-[20rem]"
            :matches="filters"
            :matchers="matchers"
            :location="SavedFilterLocation.HISTORY_DEPOSITS_WITHDRAWALS"
            @update:matches="setFilter($event)"
          />
        </template>
        <IgnoreButtons
          :disabled="selected.length === 0 || loading"
          @ignore="ignore($event)"
        />
        <div
          v-if="selected.length > 0"
          class="flex flex-row items-center gap-2"
        >
          {{ t('deposits_withdrawals.selected', { count: selected.length }) }}
          <RuiButton
            variant="text"
            size="sm"
            @click="selected = []"
          >
            {{ t('common.actions.clear_selection') }}
          </RuiButton>
        </div>
      </HistoryTableActions>

      <CollectionHandler
        :collection="assetMovements"
        @set-page="setPage($event)"
      >
        <template #default="{ data, limit, total, showUpgradeRow, itemLength }">
          <RuiDataTable
            v-model="value"
            :expanded.sync="expanded"
            :cols="tableHeaders"
            :rows="data"
            :loading="isLoading || loading"
            :loading-text="t('deposits_withdrawals.loading')"
            :pagination.sync="pagination"
            :pagination-modifiers="{ external: true }"
            :sort.sync="sort"
            :sort-modifiers="{ external: true }"
            :server-items-length="itemLength"
            class="asset-movements"
            outlined
            row-attr="identifier"
            single-expand
            sticky-header
            :item-class="getItemClass"
          >
            <template #item.ignoredInAccounting="{ row }">
              <IgnoredInAcountingIcon v-if="row.ignoredInAccounting" />
              <span v-else />
            </template>
            <template #item.location="{ row }">
              <LocationDisplay :identifier="row.location" />
            </template>
            <template #item.category="{ row }">
              <BadgeDisplay
                :color="
                  row.category.toLowerCase() === 'withdrawal'
                    ? 'grey'
                    : 'green'
                "
              >
                {{ row.category }}
              </BadgeDisplay>
            </template>
            <template #item.asset="{ row }">
              <AssetDetails
                opens-details
                :asset="row.asset"
              />
            </template>
            <template #item.amount="{ row }">
              <AmountDisplay
                class="deposits-withdrawals__movement__amount"
                :value="row.amount"
              />
            </template>
            <template #item.fee="{ row }">
              <AmountDisplay
                class="deposits-withdrawals__trade__fee"
                :asset="row.feeAsset"
                :value="row.fee"
              />
            </template>
            <template #item.timestamp="{ row }">
              <DateDisplay :timestamp="row.timestamp" />
            </template>
            <template #expanded-item="{ row }">
              <DepositWithdrawalDetails :item="row" />
            </template>
            <template
              v-if="showUpgradeRow"
              #body.prepend="{ colspan }"
            >
              <UpgradeRow
                :limit="limit"
                :total="total"
                :colspan="colspan"
                :label="t('deposits_withdrawals.label')"
              />
            </template>
          </RuiDataTable>
        </template>
      </CollectionHandler>
    </RuiCard>
  </TablePageLayout>
</template>
