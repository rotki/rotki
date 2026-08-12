<script setup lang="ts">
import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type {
  Airdrop,
  Airdrops,
  PoapDeliveryDetails,
} from '@/modules/airdrops/airdrops';
import { type BigNumber, Zero } from '@rotki/common';
import { msg } from '@/message-key';
import AirdropDisplay from '@/modules/airdrops/AirdropDisplay.vue';
import PoapDeliveryAirdrops from '@/modules/airdrops/PoapDeliveryAirdrops.vue';
import { airdropParams, useAirdropFields } from '@/modules/airdrops/use-airdrop-fields';
import { useAirdrops } from '@/modules/airdrops/use-airdrops';
import { AssetAmountDisplay, ValueDisplay } from '@/modules/assets/amount-display/components';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.defi_sub.airdrops'), icon: 'lu-gift', section: 1, order: 90, drawer: 'airdrops' },
  },
});

type AirdropWithIndex = Omit<Airdrop, 'amount'> & { index: number; amount: BigNumber };

const { t } = useI18n({ useScope: 'global' });
const { airdrops, fetchAirdrops, loading } = useAirdrops();
const hideUnknownAlert = useLocalStorage('rotki.airdrops.hide_unknown_alert', false);

const sort = ref<DataTableSortData<AirdropWithIndex>>([]);

const expanded = ref<AirdropWithIndex[]>([]);
const status = ref<string>('');
const pagination = ref<TablePaginationData>();
const selectedAddresses = ref<string[]>([]);

const refreshTooltip = computed<string>(() =>
  t('helpers.refresh_header.tooltip', {
    title: t('airdrops.title').toLocaleLowerCase(),
  }),
);

const airdropAddresses = computed<string[]>(() => Object.keys(get(airdrops)));

const fields = useAirdropFields(airdropAddresses);
const pillLabels = usePillBarLabels();
const pillParams = airdropParams(selectedAddresses, status);

const rows = computed<AirdropWithIndex[]>(() => {
  const data = filterByAddress(get(airdrops), get(selectedAddresses));
  return data
    .filter((airdrop) => {
      const currentStatus = get(status);
      const currentTime = Date.now() / 1000;
      switch (currentStatus) {
        case 'unknown':
          return !airdrop.hasDecoder;
        case 'missed':
          return (
            airdrop.hasDecoder
            && !airdrop.claimed
            && typeof airdrop.cutoffTime !== 'undefined'
            && airdrop.cutoffTime !== null
            && airdrop.cutoffTime < currentTime
          );
        case 'unclaimed':
          return airdrop.hasDecoder && !airdrop.claimed;
        case 'claimed':
          return airdrop.claimed;
        default:
          return true;
      }
    })
    .map((value, index) => ({
      ...value,
      amount: value.amount ?? Zero,
      index,
    }));
});

const cols = computed<DataTableColumn<AirdropWithIndex>[]>(() => [
  {
    key: 'source',
    label: t('airdrops.headers.source'),
    sortable: true,
    width: '200px',
  },
  {
    key: 'address',
    label: t('common.address'),
    sortable: true,
  },
  {
    align: 'end',
    key: 'amount',
    label: t('common.amount'),
    sortable: true,
  },
  {
    key: 'claimed',
    label: t('common.status'),
  },
]);

useRememberTableSorting<AirdropWithIndex>(TableId.AIRDROP, sort, cols);

function filterByAddress(data: Airdrops, addresses: string[]): Airdrop[] {
  const result: Airdrop[] = [];
  for (const address in data) {
    if (addresses.length > 0 && !addresses.includes(address))
      continue;

    const airdrop = data[address];
    for (const source in airdrop) {
      const element = airdrop[source];
      // Only poap deliveries are stored as an array, so this is also the poap branch.
      if (Array.isArray(element)) {
        result.push({
          address,
          details: element.map(detail => ({
            ...detail,
          })),
          source,
        });
      }
      else {
        result.push({
          address,
          source,
          ...element,
        });
      }
    }
  }
  return result;
}

function hasDetails(details?: PoapDeliveryDetails[]): details is PoapDeliveryDetails[] {
  return !!details && details.length > 0;
}

function expand(item: AirdropWithIndex) {
  set(expanded, get(expanded).includes(item) ? [] : [item]);
}

onMounted(async () => {
  await fetchAirdrops();
});

watch([status, selectedAddresses], () => {
  set(pagination, { ...get(pagination), page: 1 });
});
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.defi_sub.airdrops')]">
    <template #buttons>
      <RuiTooltip :open-delay="400">
        <template #activator>
          <RuiButton
            variant="outlined"
            color="primary"
            size="lg"
            :loading="loading"
            data-testid="airdrop-refresh"
            @click="fetchAirdrops()"
          >
            <template #prepend>
              <RuiIcon name="lu-refresh-ccw" />
            </template>
            {{ t('common.refresh') }}
          </RuiButton>
        </template>
        {{ refreshTooltip }}
      </RuiTooltip>
    </template>

    <RuiCard>
      <PillFilterBar
        v-model:params="pillParams"
        class="mb-4"
        :fields="fields"
        :labels="pillLabels"
      />

      <RuiAlert
        v-if="!hideUnknownAlert && status === 'unknown'"
        type="info"
        class="mb-4"
        closeable
        data-testid="airdrop-unknown-alert"
        @close="hideUnknownAlert = true"
      >
        {{ t('airdrops.unknown_info') }}
      </RuiAlert>

      <RuiDataTable
        v-model:pagination="pagination"
        v-model:expanded="expanded"
        v-model:sort="sort"
        outlined
        data-testid="airdrop-table"
        :rows="rows"
        :cols="cols"
        :loading="loading"
        single-expand
        row-attr="index"
      >
        <template #item.address="{ row }">
          <HashLink
            :text="row.address"
            location="eth"
          />
        </template>
        <template #item.amount="{ row }">
          <AssetAmountDisplay
            v-if="!hasDetails(row.details) && row.asset"
            :asset="row.asset"
            :amount="row.amount"
          />
          <ValueDisplay
            v-else-if="!hasDetails(row.details)"
            :value="row.amount"
          />
          <span v-else>{{ row.details.length }}</span>
        </template>
        <template #item.claimed="{ row: { claimed, cutoffTime, hasDecoder } }">
          <RuiTooltip
            v-if="!hasDecoder"
            :popper="{ placement: 'top' }"
            :open-delay="400"
            tooltip-class="max-w-[12rem]"
          >
            <template #activator>
              <RuiChip
                color="info"
                size="sm"
              >
                {{ t('common.unknown') }}
              </RuiChip>
            </template>

            {{ t('airdrops.unknown_tooltip') }}
          </RuiTooltip>
          <RuiChip
            v-else
            :color="claimed ? 'success' : 'grey'"
            size="sm"
          >
            {{
              claimed
                ? t('common.claimed')
                : cutoffTime && cutoffTime < Date.now() / 1000
                  ? t('common.missed')
                  : t('common.unclaimed')
            }}
          </RuiChip>
        </template>
        <template #item.source="{ row }">
          <AirdropDisplay
            :source="row.source"
            :icon-url="row.iconUrl"
            :icon="row.icon"
          />
        </template>
        <template #item.expand="{ row }">
          <ExternalLink
            v-if="!hasDetails(row.details)"
            :url="row.link"
            custom
          >
            <RuiButton
              variant="text"
              color="primary"
              icon
            >
              <RuiIcon
                size="16"
                name="lu-external-link"
              />
            </RuiButton>
          </ExternalLink>
          <RuiTableRowExpander
            v-else
            :expanded="expanded.includes(row)"
            @click="expand(row)"
          />
        </template>
        <template #expanded-item="{ row }">
          <PoapDeliveryAirdrops
            v-if="hasDetails(row.details)"
            :items="row.details"
          />
        </template>
      </RuiDataTable>
    </RuiCard>
  </TablePageLayout>
</template>
