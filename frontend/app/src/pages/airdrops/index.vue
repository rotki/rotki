<script setup lang="ts">
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import type { TaskMeta } from '@/types/task';
import type { DataTableColumn, TablePaginationData } from '@rotki/ui-library';
import AirdropDisplay from '@/components/defi/airdrops/AirdropDisplay.vue';
import PoapDeliveryAirdrops from '@/components/defi/airdrops/PoapDeliveryAirdrops.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import { useDefiApi } from '@/composables/api/defi';
import HashLink from '@/modules/common/links/HashLink.vue';
import { useNotificationsStore } from '@/store/notifications';
import { useTaskStore } from '@/store/tasks';
import {
  type Airdrop,
  AIRDROP_POAP,
  Airdrops,
  type PoapDelivery,
  type PoapDeliveryDetails,
} from '@/types/defi/airdrops';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';
import { logger } from '@/utils/logging';
import { type BigNumber, Blockchain, Zero } from '@rotki/common';

type AirdropWithIndex = Omit<Airdrop, 'amount'> & { index: number; amount: BigNumber };

type Statuses = '' | 'unknown' | 'unclaimed' | 'claimed' | 'missed';
const ETH = Blockchain.ETH;
const { t } = useI18n();
const { awaitTask } = useTaskStore();
const { notify } = useNotificationsStore();
const { fetchAirdrops: fetchAirdropsCaller } = useDefiApi();
const hideUnknownAlert = useLocalStorage('rotki.airdrops.hide_unknown_alert', false);

const airdrops = ref<Airdrops>({});
const expanded = ref<AirdropWithIndex[]>([]);
const loading = ref<boolean>(false);
const status = ref<Statuses>('');
const pagination = ref<TablePaginationData>();
const selectedAccounts = ref<BlockchainAccount<AddressData>[]>([]);
const statusFilters = ref<{ text: string; value: Statuses }[]>([
  { text: t('common.all'), value: '' },
  { text: t('common.unknown'), value: 'unknown' },
  { text: t('common.unclaimed'), value: 'unclaimed' },
  { text: t('common.claimed'), value: 'claimed' },
  { text: t('common.missed'), value: 'missed' },
]);

const refreshTooltip = computed<string>(() =>
  t('helpers.refresh_header.tooltip', {
    title: t('airdrops.title').toLocaleLowerCase(),
  }),
);

const airdropAddresses = computed<string[]>(() => Object.keys(get(airdrops)));

const rows = computed<AirdropWithIndex[]>(() => {
  const addresses = get(selectedAccounts).map(account => getAccountAddress(account));
  const data = filterByAddress(get(airdrops), addresses);
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
    width: '200px',
  },
  {
    key: 'address',
    label: t('common.address'),
  },
  {
    align: 'end',
    key: 'amount',
    label: t('common.amount'),
  },
  {
    key: 'claimed',
    label: t('common.status'),
  },
]);

function filterByAddress(data: Airdrops, addresses: string[]): Airdrop[] {
  const result: Airdrop[] = [];
  for (const address in data) {
    if (addresses.length > 0 && !addresses.includes(address))
      continue;

    const airdrop = data[address];
    for (const source in airdrop) {
      const element = airdrop[source];
      if (source === AIRDROP_POAP) {
        const details = element as PoapDelivery[];
        result.push({
          address,
          details: details.map(detail => ({
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

async function fetchAirdrops() {
  set(loading, true);
  try {
    const { taskId } = await fetchAirdropsCaller();
    const { result } = await awaitTask<Airdrops, TaskMeta>(taskId, TaskType.DEFI_AIRDROPS, {
      title: t('actions.defi.airdrops.task.title'),
    });
    set(airdrops, Airdrops.parse(result));
  }
  catch (error: any) {
    if (!isTaskCancelled(error)) {
      logger.error(error);
      notify({
        display: true,
        message: t('actions.defi.airdrops.error.description', {
          error: error.message,
        }),
        title: t('actions.defi.airdrops.error.title'),
      });
    }
  }
  finally {
    set(loading, false);
  }
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

watch([status, selectedAccounts], () => {
  set(pagination, { ...get(pagination), page: 1 });
});
</script>

<template>
  <TablePageLayout :title="[t('navigation_menu.defi'), t('navigation_menu.defi_sub.airdrops')]">
    <template #buttons>
      <RuiTooltip :open-delay="400">
        <template #activator>
          <RuiButton
            variant="outlined"
            color="primary"
            :loading="loading"
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
      <div class="flex flex-col md:flex-row flex-wrap items-start gap-4 mb-4">
        <BlockchainAccountSelector
          v-model="selectedAccounts"
          class="w-full flex-1 !shadow-none !border-none !p-0"
          dense
          outlined
          :chains="[ETH]"
          :usable-addresses="airdropAddresses"
        />
        <RuiMenuSelect
          v-model="status"
          :options="statusFilters"
          class="w-full flex-1"
          key-attr="value"
          text-attr="text"
          dense
          hide-details
          variant="outlined"
        />
      </div>

      <RuiAlert
        v-if="!hideUnknownAlert && status === 'unknown'"
        type="info"
        class="mb-4"
        closeable
        @close="hideUnknownAlert = true"
      >
        {{ t('airdrops.unknown_info') }}
      </RuiAlert>

      <RuiDataTable
        v-model:pagination="pagination"
        v-model:expanded="expanded"
        outlined
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
          <AmountDisplay
            v-if="!hasDetails(row.details)"
            :value="row.amount"
            :asset="row.asset"
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
