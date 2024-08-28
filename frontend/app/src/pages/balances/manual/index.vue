<script setup lang="ts">
import { TRADE_LOCATION_EXTERNAL } from '@/data/defaults';
import { BalanceType } from '@/types/balances';
import ManualBalancesForm from '@/components/accounts/manual-balances/ManualBalancesForm.vue';
import { NoteLocation } from '@/types/notes';
import type { ManualBalance, RawManualBalance } from '@/types/manual-balances';

definePage({
  name: 'accounts-balances-manual',
  meta: {
    noteLocation: NoteLocation.ACCOUNTS_BALANCES_MANUAL,
  },
});

const balance = ref<ManualBalance | RawManualBalance>();
const loading = ref(false);
const errorMessages = ref<Record<string, string[]>>({});
const form = ref<InstanceType<typeof ManualBalancesForm>>();

const { t } = useI18n();

const isEdit = computed(() => isDefined(balance) && 'identifier' in get(balance));

const dialogTitle = computed<string>(() => {
  if (get(isEdit))
    return t('manual_balances.dialog.edit.title');
  return t('manual_balances.dialog.add.title');
});

const dialogSubtitle = computed<string>(() => {
  if (get(isEdit))
    return t('manual_balances.dialog.edit.subtitle');
  return '';
});

const router = useRouter();
const route = useRoute('accounts-balances-manual');

const { setMessage } = useMessageStore();
const { save: saveBalance, fetchManualBalances } = useManualBalancesStore();
const { refreshPrices } = useBalances();
const { fetchAssociatedLocations } = useHistoryStore();

async function save() {
  if (!isDefined(balance))
    return;

  set(loading, true);

  await get(form)?.savePrice();

  const status = await saveBalance(get(balance));

  startPromise(refreshPrices(true));

  if (status.success) {
    set(balance, undefined);
    set(loading, false);
    return true;
  }

  if (status.message) {
    if (typeof status.message !== 'string') {
      set(errorMessages, status.message);
      await get(form)?.validate();
    }
    else {
      const obj = { message: status.message };
      setMessage({
        description: get(isEdit)
          ? t('actions.manual_balances.edit.error.description', obj)
          : t('actions.manual_balances.add.error.description', obj),
      });
    }
  }
  set(loading, false);
  return false;
}

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
    :title="[t('navigation_menu.accounts_balances'), t('navigation_menu.accounts_balances_sub.manual_balances')]"
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
    <BigDialog
      :display="!!balance"
      :title="dialogTitle"
      :subtitle="dialogSubtitle"
      :loading="loading"
      :primary-action="t('common.actions.save')"
      @confirm="save()"
      @cancel="balance = undefined"
    >
      <ManualBalancesForm
        v-if="balance"
        ref="form"
        v-model="balance"
        v-model:error-messages="errorMessages"
        :submitting="loading"
      />
    </BigDialog>
  </TablePageLayout>
</template>
