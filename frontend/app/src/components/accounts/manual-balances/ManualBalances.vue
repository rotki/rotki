<template>
  <fragment>
    <v-btn
      v-blur
      fixed
      fab
      bottom
      right
      dark
      color="primary"
      class="manual-balances__add-balance"
      @click="add()"
    >
      <v-icon> mdi-plus </v-icon>
    </v-btn>
    <manual-balance-table
      :title="$t('manual_balances.balances')"
      :balances="manualBalances"
      :loading="loading"
      @edit="edit($event)"
      @refresh="refresh"
    />
    <manual-balance-table
      :title="$t('manual_balances.liabilities')"
      class="mt-8"
      :balances="manualLiabilities"
      :loading="loading"
      @edit="edit($event)"
      @refresh="refresh"
    />
    <big-dialog
      :display="openDialog"
      :title="dialogTitle"
      :subtitle="dialogSubtitle"
      :action-disabled="dialogDisabled || !valid || dialogLoading"
      :loading="dialogLoading"
      primary-action="Save"
      @confirm="save()"
      @cancel="cancel()"
    >
      <manual-balances-form ref="form" v-model="valid" :edit="balanceToEdit" />
    </big-dialog>
  </fragment>
</template>

<script lang="ts">
import { defineComponent, onMounted, Ref, ref } from '@vue/composition-api';
import ManualBalancesForm from '@/components/accounts/manual-balances/ManualBalancesForm.vue';
import ManualBalanceTable from '@/components/accounts/manual-balances/ManualBalanceTable.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import Fragment from '@/components/helper/Fragment';
import { setupManualBalances } from '@/composables/balances';
import { useRouter } from '@/composables/common';
import i18n from '@/i18n';
import { ManualBalance } from '@/services/balances/types';

const setupDialog = (balanceToEdit: Ref<ManualBalance | null>) => {
  const dialogTitle = ref('');
  const dialogSubtitle = ref('');
  const openDialog = ref(false);
  const dialogDisabled = ref(false);
  const dialogLoading = ref(false);

  const add = () => {
    dialogTitle.value = i18n.t('manual_balances.dialog.add.title').toString();
    dialogSubtitle.value = '';
    openDialog.value = true;
  };

  const edit = (balance: ManualBalance) => {
    balanceToEdit.value = balance;
    dialogTitle.value = i18n.t('manual_balances.dialog.edit.title').toString();
    dialogSubtitle.value = i18n
      .t('manual_balances.dialog.edit.subtitle')
      .toString();
    openDialog.value = true;
  };

  const cancel = () => {
    openDialog.value = false;
    balanceToEdit.value = null;
  };

  return {
    add,
    edit,
    cancel,
    dialogTitle,
    dialogSubtitle,
    openDialog,
    dialogDisabled,
    dialogLoading
  };
};

const ManualBalances = defineComponent({
  name: 'ManualBalances',
  components: {
    ManualBalanceTable,
    Fragment,
    ManualBalancesForm,
    BigDialog
  },
  setup() {
    const form = ref<any | null>(null);
    const balanceToEdit: Ref<ManualBalance | null> = ref(null);
    const loading = ref(false);
    const valid = ref(false);
    const dialog = setupDialog(balanceToEdit);
    const { fetchManualBalances, manualBalances, manualLiabilities } =
      setupManualBalances();

    const refresh = async () => {
      loading.value = true;
      await fetchManualBalances();
      loading.value = false;
    };

    const save = async () => {
      const { dialogDisabled, dialogLoading, openDialog } = dialog;
      dialogDisabled.value = true;
      dialogLoading.value = true;
      const success = await form.value?.save();
      dialogDisabled.value = false;
      dialogLoading.value = false;

      if (!success) {
        return;
      }
      openDialog.value = false;
      balanceToEdit.value = null;
    };

    const router = useRouter();
    onMounted(() => {
      const { currentRoute } = router;
      const { openDialog } = dialog;
      openDialog.value = !!currentRoute.query.add;
    });

    return {
      ...dialog,
      loading,
      valid,
      form,
      balanceToEdit,
      manualBalances,
      manualLiabilities,
      refresh,
      save
    };
  }
});
export default ManualBalances;
</script>
