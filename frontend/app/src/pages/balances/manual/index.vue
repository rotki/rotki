<script setup lang="ts">
import type { Ref } from 'vue';
import type { ManualBalance } from '@/types/manual-balances';

const balanceToEdit: Ref<ManualBalance | null> = ref(null);
const loading = ref(false);

const store = useManualBalancesStore();
const { fetchManualBalances } = store;
const { manualBalances, manualLiabilities } = storeToRefs(store);

const dialogTitle = ref('');
const dialogSubtitle = ref('');

const { t } = useI18n();

const {
  openDialog,
  submitting,
  setOpenDialog,
  trySubmit,
  closeDialog,
  setPostSubmitFunc,
} = useManualBalancesForm();

function add() {
  set(dialogTitle, t('manual_balances.dialog.add.title').toString());
  set(dialogSubtitle, '');
  setOpenDialog(true);
}

function edit(balance: ManualBalance) {
  set(balanceToEdit, balance);
  set(dialogTitle, t('manual_balances.dialog.edit.title').toString());
  set(dialogSubtitle, t('manual_balances.dialog.edit.subtitle').toString());
  setOpenDialog(true);
}

function cancelForm() {
  closeDialog();
  set(balanceToEdit, null);
}

async function refresh() {
  set(loading, true);
  await fetchManualBalances();
  set(loading, false);
}

function postSubmit() {
  set(balanceToEdit, null);
}

setPostSubmitFunc(postSubmit);

const router = useRouter();
onMounted(async () => {
  const { currentRoute } = router;
  if (currentRoute.query.add) {
    add();
    await router.replace({ query: {} });
  }
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
      :balances="manualBalances"
      :loading="loading"
      @edit="edit($event)"
      @refresh="refresh()"
    />
    <ManualBalanceTable
      data-cy="manual-liabilities"
      :title="t('manual_balances.liabilities')"
      class="mt-8"
      :balances="manualLiabilities"
      :loading="loading"
      @edit="edit($event)"
      @refresh="refresh()"
    />
    <BigDialog
      :display="openDialog"
      :title="dialogTitle"
      :subtitle="dialogSubtitle"
      :loading="submitting"
      :primary-action="t('common.actions.save')"
      @confirm="trySubmit()"
      @cancel="cancelForm()"
    >
      <ManualBalancesForm :edit="balanceToEdit" />
    </BigDialog>
  </TablePageLayout>
</template>
