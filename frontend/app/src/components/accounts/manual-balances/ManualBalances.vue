<template>
  <fragment>
    <v-btn
      v-blur
      fixed
      bottom
      right
      :fab="!$vuetify.breakpoint.xl"
      :rounded="$vuetify.breakpoint.xl"
      :x-large="$vuetify.breakpoint.xl"
      color="primary"
      class="manual-balances__add-balance"
      @click="add()"
    >
      <v-icon> mdi-plus </v-icon>
      <div v-if="$vuetify.breakpoint.xl" class="ml-2">
        {{ $tc('manual_balances.add_manual_balance') }}
      </div>
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
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import ManualBalancesForm from '@/components/accounts/manual-balances/ManualBalancesForm.vue';
import ManualBalanceTable from '@/components/accounts/manual-balances/ManualBalanceTable.vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import Fragment from '@/components/helper/Fragment';
import { useRouter } from '@/composables/common';
import i18n from '@/i18n';
import { BalanceType, ManualBalance } from '@/services/balances/types';
import { useManualBalancesStore } from '@/store/balances/manual';

const setupDialog = (balanceToEdit: Ref<ManualBalance | null>) => {
  const dialogTitle = ref('');
  const dialogSubtitle = ref('');
  const openDialog = ref(false);
  const dialogDisabled = ref(false);
  const dialogLoading = ref(false);

  const add = () => {
    set(dialogTitle, i18n.t('manual_balances.dialog.add.title').toString());
    set(dialogSubtitle, '');
    set(openDialog, true);
  };

  const edit = (balance: ManualBalance) => {
    set(balanceToEdit, balance);
    set(dialogTitle, i18n.t('manual_balances.dialog.edit.title').toString());
    set(
      dialogSubtitle,
      i18n.t('manual_balances.dialog.edit.subtitle').toString()
    );
    set(openDialog, true);
  };

  const cancel = () => {
    set(openDialog, false);
    set(balanceToEdit, null);
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

    const store = useManualBalancesStore();
    const { fetchManualBalances } = store;
    const { manualBalances, manualLiabilities } = storeToRefs(store);

    const refresh = async () => {
      set(loading, true);
      await fetchManualBalances();
      set(loading, false);
    };

    const save = async () => {
      const { dialogDisabled, dialogLoading, openDialog } = dialog;
      set(dialogDisabled, true);
      set(dialogLoading, true);
      const success = await get(form)?.save();
      set(dialogDisabled, false);
      set(dialogLoading, false);

      if (!success) {
        return;
      }
      set(openDialog, false);
      set(balanceToEdit, null);
    };

    const router = useRouter();
    onMounted(() => {
      const { currentRoute } = router;
      const { add } = dialog;
      if (currentRoute.query.add) {
        add();
        router.replace({ query: {} });
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
      set(intersections, {
        ...get(intersections),
        [value]: entries[0].isIntersecting
      });
    };

    const observers = {
      [BalanceType.ASSET]: (entries: IntersectionObserverEntry[]) =>
        updateWhenRatio(entries, BalanceType.ASSET),
      [BalanceType.LIABILITY]: (entries: IntersectionObserverEntry[]) =>
        updateWhenRatio(entries, BalanceType.LIABILITY)
    };

    const context = computed(() => {
      const intersect = get(intersections);
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
