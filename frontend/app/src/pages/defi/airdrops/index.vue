<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import {
  AIRDROP_POAP,
  type Airdrop,
  type AirdropDetail,
  Airdrops,
  type PoapDelivery,
} from '@/types/defi/airdrops';
import { TaskType } from '@/types/task-type';
import AirdropDisplay from '@/components/defi/airdrops/AirdropDisplay.vue';
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import type { DataTableColumn } from '@rotki/ui-library-compat';
import type { TaskMeta } from '@/types/task';

type Statuses = '' | 'unknown' | 'unclaimed' | 'claimed';
const ETH = Blockchain.ETH;
const { t } = useI18n();
const { awaitTask } = useTaskStore();
const { notify } = useNotificationsStore();
const { fetchAirdrops: fetchAirdropsCaller } = useDefiApi();
const hideUnknownAlert = useLocalStorage('rotki.airdrops.hide_unknown_alert', false);

const expanded: Ref<Airdrop[]> = ref([]);
const selectedAccounts: Ref<BlockchainAccount<AddressData>[]> = ref([]);
const statusFilters: Ref<{ text: string; value: Statuses }[]> = ref([
  { text: t('common.all'), value: '' },
  { text: t('common.unknown'), value: 'unknown' },
  { text: t('common.unclaimed'), value: 'unclaimed' },
  { text: t('common.claimed'), value: 'claimed' },
]);
const status: Ref<Statuses> = ref('unclaimed');
const loading: Ref<boolean> = ref(false);

const refreshTooltip: ComputedRef<string> = computed(() =>
  t('helpers.refresh_header.tooltip', {
    title: t('airdrops.title').toLocaleLowerCase(),
  }),
);
const airdrops: Ref<Airdrops> = ref({});

const airdropAddresses = computed(() => Object.keys(get(airdrops)));

const entries = computed(() => {
  const addresses = get(selectedAccounts).map(account => getAccountAddress(account));
  const airdrops = get(airdropList(addresses));
  return airdrops
    .filter((airdrop) => {
      const currentStatus = get(status);
      switch (currentStatus) {
        case 'unknown':
          return airdrop.missingDecoder;
        case 'unclaimed':
          return !airdrop.claimed && !airdrop.missingDecoder;
        case 'claimed':
          return airdrop.claimed;
        default:
          return true;
      }
    })
    .map((value, index) => ({
      ...value,
      index,
    }));
});

const tableHeaders = computed<DataTableColumn[]>(() => [
  {
    label: t('airdrops.headers.source'),
    key: 'source',
    width: '200px',
  },
  {
    label: t('common.address'),
    key: 'address',
  },
  {
    label: t('common.amount'),
    key: 'amount',
    align: 'end',
  },
  {
    label: t('common.status'),
    key: 'claimed',
  },
]);

function airdropList(addresses: string[]): ComputedRef<Airdrop[]> {
  return computed(() => {
    const result: Airdrop[] = [];
    const data = get(airdrops);
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
            source,
            details: details.map(({ link, name, event }) => ({
              amount: bigNumberify('1'),
              link,
              name,
              event,
              claimed: false,
            })),
          });
        }
        else {
          const { amount, asset, link, claimed, missingDecoder } = element as AirdropDetail;
          result.push({
            address,
            amount,
            link,
            source,
            asset,
            claimed,
            missingDecoder,
          });
        }
      }
    }
    return result;
  });
}

async function fetchAirdrops() {
  set(loading, true);
  try {
    const { taskId } = await fetchAirdropsCaller();
    const { result } = await awaitTask<Airdrops, TaskMeta>(
      taskId,
      TaskType.DEFI_AIRDROPS,
      {
        title: t('actions.defi.airdrops.task.title').toString(),
      },
    );
    set(airdrops, Airdrops.parse(result));
  }
  catch (error: any) {
    if (!isTaskCancelled(error)) {
      logger.error(error);
      notify({
        title: t('actions.defi.airdrops.error.title').toString(),
        message: t('actions.defi.airdrops.error.description', {
          error: error.message,
        }).toString(),
        display: true,
      });
    }
  }
  finally {
    set(loading, false);
  }
}

const hasDetails = (source: string): boolean => [AIRDROP_POAP].includes(source);

function expand(item: Airdrop) {
  set(expanded, get(expanded).includes(item) ? [] : [item]);
}

onMounted(async () => {
  await fetchAirdrops();
});
</script>

<template>
  <TablePageLayout
    :title="[t('navigation_menu.defi'), t('navigation_menu.defi_sub.airdrops')]"
  >
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
              <RuiIcon name="refresh-line" />
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
          multiple
          class="w-full flex-1 !shadow-none !border-none !p-0"
          no-padding
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
          full-width
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
        outlined
        :rows="entries"
        :cols="tableHeaders"
        :loading="loading"
        single-expand
        :expanded.sync="expanded"
        row-attr="index"
      >
        <template #item.address="{ row }">
          <HashLink :text="row.address" />
        </template>
        <template #item.amount="{ row }">
          <AmountDisplay
            v-if="!hasDetails(row.source)"
            :value="row.amount"
            :asset="row.asset"
          />
          <span v-else>{{ row.details.length }}</span>
        </template>
        <template #item.claimed="{ row: { claimed, missingDecoder } }">
          <RuiTooltip
            v-if="missingDecoder"
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
            {{ claimed ? t('common.claimed') : t('common.unclaimed') }}
          </RuiChip>
        </template>
        <template #item.source="{ row }">
          <AirdropDisplay
            :source="row.source"
            :icon-url="row.iconUrl"
          />
        </template>
        <template #item.expand="{ row }">
          <ExternalLink
            v-if="!hasDetails(row.source)"
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
                name="external-link-line"
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
            v-if="hasDetails(row.source)"
            :items="row.details"
          />
        </template>
      </RuiDataTable>
    </RuiCard>
  </TablePageLayout>
</template>
