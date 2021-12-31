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
      v-intersect="{
        handler: observers.asset,
        options: {
          threshold
        }
      }"
      data-cy="manual-balances"
      :title="$t('manual_balances.balances')"
      :balances="manualBalances"
      :loading="loading"
      @edit="edit($event)"
      @refresh="refresh"
    />
    <manual-balance-table
      v-intersect="{
        handler: observers.liability,
        options: {
          threshold
        }
      }"
      data-cy="manual-liabilities"
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
      <manual-balances-form
        ref="form"
        v-model="valid"
        :edit="balanceToEdit"
        :context="context"
      />
    </big-dialog>
  </fragment>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  onMounted,
  Ref,
  ref
} from '@vue/composition-api';
import ManualBalancesForm from '@/components/accounts/manual-balances/ManualBalancesForm.vue';
import ManualBalanceTable from '@/components/accounts/manual-balances/ManualBalanceTable.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import Fragment from '@/components/helper/Fragment';
import { setupManualBalances } from '@/composables/balances';
import { useRouter } from '@/composables/common';
import i18n from '@/i18n';
import { BalanceType, ManualBalance } from '@/services/balances/types';

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
      const { add } = dialog;
      if (currentRoute.query.add) {
        add();
      }
    });

    const intersections = ref({
      [BalanceType.ASSET]: false,
      [BalanceType.LIABILITY]: false
    });

    const updateWhenRatio = (
      entries: IntersectionObserverEntry[],
      value: BalanceType
    ) => {
      intersections.value = {
        ...intersections.value,
        [value]: entries[0].isIntersecting
      };
    };

    const observers = {
      [BalanceType.ASSET]: (entries: IntersectionObserverEntry[]) =>
        updateWhenRatio(entries, BalanceType.ASSET),
      [BalanceType.LIABILITY]: (entries: IntersectionObserverEntry[]) =>
        updateWhenRatio(entries, BalanceType.LIABILITY)
    };

    const context = computed(() => {
      const intersect = intersections.value;
      return intersect.liability ? BalanceType.LIABILITY : BalanceType.ASSET;
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
      save,
      observers,
      context,
      threshold: [1]
    };
  }
});
export default ManualBalances;
</script>
