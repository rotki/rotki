<script setup lang="ts">
import { startPromise } from '@shared/utils';
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import { BalanceType } from '@/types/balances';
import { NoteLocation } from '@/types/notes';
import { BalanceSource } from '@/types/settings/frontend-settings';
import { useManualBalancesStore } from '@/store/balances/manual';
import { useHistoryStore } from '@/store/history';
import ManualBalancesDialog from '@/components/accounts/manual-balances/ManualBalancesDialog.vue';
import ManualBalanceTable from '@/components/accounts/manual-balances/ManualBalanceTable.vue';
import HideSmallBalances from '@/components/settings/HideSmallBalances.vue';
import PriceRefresh from '@/components/helper/PriceRefresh.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import type { ManualBalance, RawManualBalance } from '@/types/manual-balances';

definePage({
  meta: {
    noteLocation: NoteLocation.BALANCES_MANUAL,
  },
  name: 'balances-manual',
  props: true,
});

const props = defineProps<{
  tab: string;
}>();

const balance = ref<ManualBalance | RawManualBalance>();

const { t } = useI18n();
const router = useRouter();
const route = useRoute('balances-manual');

const { fetchManualBalances } = useManualBalancesStore();
const { fetchAssociatedLocations } = useHistoryStore();

function add() {
  set(balance, {
    amount: Zero,
    asset: '',
    balanceType: props.tab === 'liabilities' ? BalanceType.LIABILITY : BalanceType.ASSET,
    label: '',
    location: TRADE_LOCATION_EXTERNAL,
    tags: null,
  } satisfies RawManualBalance);
}

function goToTab(tab: string | number) {
  const currentRoute = get(route);
  if (currentRoute.params.tab === tab)
    return;
  router.push(`/balances/manual/${tab}`);
}

watchImmediate(route, (route) => {
  const { params } = route;

  if (!params.tab || params.tab === '0')
    router.push('/balances/manual/assets');
}, { deep: true });

onBeforeMount(async () => {
  const { query } = get(route);
  if (query.add) {
    await router.replace({ query: {} });
    startPromise(nextTick(() => add()));
  }
  await fetchManualBalances();
  await fetchAssociatedLocations();
});
</script>

<template>
  <TablePageLayout
    :title="[
      t('navigation_menu.balances'),
      t('navigation_menu.balances_sub.manual_balances'),
    ]"
  >
    <template #buttons>
      <PriceRefresh />
      <RuiButton
        color="primary"
        data-cy="manual-balances-add-button"
        @click="add()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('manual_balances.add_manual_balance') }}
      </RuiButton>
      <HideSmallBalances :source="BalanceSource.MANUAL" />
    </template>

    <div>
      <RuiTabs
        :model-value="tab"
        color="primary"
        class="border border-default rounded bg-white dark:bg-rui-grey-900 flex max-w-min mb-3"
        @update:model-value="goToTab($event)"
      >
        <RuiTab value="assets">
          {{ t('common.assets') }}
        </RuiTab>
        <RuiTab value="liabilities">
          {{ t('common.liabilities') }}
        </RuiTab>
      </RuiTabs>
      <RuiTabItems :model-value="tab">
        <RuiTabItem value="assets">
          <ManualBalanceTable
            data-cy="manual-balances"
            :title="t('manual_balances.balances')"
            type="balances"
            @edit="balance = $event"
          />
        </RuiTabItem>
        <RuiTabItem value="liabilities">
          <ManualBalanceTable
            data-cy="manual-liabilities"
            :title="t('manual_balances.liabilities')"
            type="liabilities"
            @edit="balance = $event"
          />
        </RuiTabItem>
      </RuiTabItems>
    </div>

    <ManualBalancesDialog
      v-model="balance"
      @update-tab="goToTab($event)"
    />
  </TablePageLayout>
</template>
