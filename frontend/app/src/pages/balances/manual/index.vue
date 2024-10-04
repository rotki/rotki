<script setup lang="ts">
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import { BalanceType } from '@/types/balances';
import { NoteLocation } from '@/types/notes';
import type { ManualBalance, RawManualBalance } from '@/types/manual-balances';

definePage({
  name: 'accounts-balances-manual',
  meta: {
    noteLocation: NoteLocation.ACCOUNTS_BALANCES_MANUAL,
  },
});

const balance = ref<ManualBalance | RawManualBalance>();

const { t } = useI18n();
const router = useRouter();
const route = useRoute('accounts-balances-manual');

const { fetchManualBalances } = useManualBalancesStore();
const { fetchAssociatedLocations } = useHistoryStore();

function add() {
  set(balance, {
    location: TRADE_LOCATION_EXTERNAL,
    asset: '',
    label: '',
    balanceType: BalanceType.ASSET,
    tags: null,
    amount: Zero,
  } satisfies RawManualBalance);
}

onMounted(async () => {
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
      t('navigation_menu.accounts_balances'),
      t('navigation_menu.accounts_balances_sub.manual_balances'),
    ]"
  >
    <template #buttons>
      <PriceRefresh />
      <RuiButton
        v-blur
        color="primary"
        class="manual-balances__add-balance"
        @click="add()"
      >
        <template #prepend>
          <RuiIcon name="add-line" />
        </template>
        {{ t('manual_balances.add_manual_balance') }}
      </RuiButton>
    </template>

    <ManualBalanceTable
      data-cy="manual-balances"
      :title="t('manual_balances.balances')"
      type="balances"
      @edit="balance = $event"
    />
    <ManualBalanceTable
      data-cy="manual-liabilities"
      :title="t('manual_balances.liabilities')"
      class="mt-8"
      type="liabilities"
      @edit="balance = $event"
    />
    <ManualBalancesDialog v-model="balance" />
  </TablePageLayout>
</template>
