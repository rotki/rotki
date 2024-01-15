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
import type { GeneralAccount } from '@rotki/common/lib/account';
import type { Ref } from 'vue';
import type { DataTableColumn } from '@rotki/ui-library-compat';
import type { TaskMeta } from '@/types/task';

const ETH = Blockchain.ETH;
const { t } = useI18n();
const { awaitTask } = useTaskStore();
const { notify } = useNotificationsStore();
const { fetchAirdrops: fetchAirdropsCaller } = useDefiApi();

const expanded: Ref<Airdrop[]> = ref([]);
const selectedAccounts: Ref<GeneralAccount[]> = ref([]);
const statusFilters: Ref<{ text: string; value: boolean }[]> = ref([
  { text: t('common.unclaimed'), value: false },
  { text: t('common.claimed'), value: true },
]);
const status: Ref<boolean> = ref(false);
const loading: Ref<boolean> = ref(false);

const refreshTooltip: ComputedRef<string> = computed(() =>
  t('helpers.refresh_header.tooltip', {
    title: t('airdrops.title').toLocaleLowerCase(),
  }),
);
const airdrops: Ref<Airdrops> = ref({});

const airdropAddresses = computed(() => Object.keys(get(airdrops)));

const entries = computed(() => {
  const addresses = get(selectedAccounts).map(({ address }) => address);
  const airdrops = get(airdropList(addresses));
  return airdrops
    .filter(airdrop => airdrop.claimed === get(status))
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
          const { amount, asset, link, claimed } = element as AirdropDetail;
          result.push({
            address,
            amount,
            link,
            source,
            asset,
            claimed,
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
      <div class="flex flex-row flex-wrap items-center gap-2 mb-4">
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
        <VSelect
          v-model="status"
          :items="statusFilters"
          class="w-full flex-1"
          item-value="value"
          item-text="text"
          hide-details
          dense
          outlined
        />
      </div>

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
        <template #item.claimed="{ row: { claimed } }">
          <RuiChip
            :color="claimed ? 'success' : 'grey'"
            size="sm"
          >
            {{ claimed ? t('common.claimed') : t('common.unclaimed') }}
          </RuiChip>
        </template>
        <template #item.source="{ row }">
          <AirdropDisplay :source="row.source" />
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
          <RowExpander
            v-else
            :expanded="expanded.includes(row)"
            @click="expand(row)"
          />
        </template>
        <template #expanded-item="{ row }">
          <PoapDeliveryAirdrops
            v-if="hasDetails(row.source)"
            :items="row.details"
            :colspan="tableHeaders.length"
            visible
          />
        </template>
      </RuiDataTable>
    </RuiCard>
  </TablePageLayout>
</template>
