<script setup lang="ts">
import { type Ref } from 'vue';
import Fragment from '@/components/helper/Fragment';
import { type ManualBalance } from '@/types/manual-balances';
import { BalanceType } from '@/types/balances';

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
  setPostSubmitFunc
} = useManualBalancesForm();

const add = () => {
  set(dialogTitle, t('manual_balances.dialog.add.title').toString());
  set(dialogSubtitle, '');
  setOpenDialog(true);
};

const edit = (balance: ManualBalance) => {
  set(balanceToEdit, balance);
  set(dialogTitle, t('manual_balances.dialog.edit.title').toString());
  set(dialogSubtitle, t('manual_balances.dialog.edit.subtitle').toString());
  setOpenDialog(true);
};

const cancelForm = () => {
  closeDialog();
  set(balanceToEdit, null);
};

const refresh = async () => {
  set(loading, true);
  await fetchManualBalances();
  set(loading, false);
};

const postSubmit = async () => {
  set(balanceToEdit, null);
};

setPostSubmitFunc(postSubmit);

const router = useRouter();
onMounted(async () => {
  const { currentRoute } = router;
  if (currentRoute.query.add) {
    add();
    await router.replace({ query: {} });
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

const threshold = [1];

const { xl } = useDisplay();
</script>

<template>
  <fragment>
    <v-row justify="end" class="mb-5">
      <v-col cols="auto">
        <price-refresh />
      </v-col>
    </v-row>
    <v-btn
      v-blur
      fixed
      bottom
      right
      :fab="!xl"
      :rounded="xl"
      :x-large="xl"
      color="primary"
      class="manual-balances__add-balance"
      @click="add()"
    >
      <v-icon> mdi-plus </v-icon>
      <div v-if="xl" class="ml-2">
        {{ t('manual_balances.add_manual_balance') }}
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
      :title="t('manual_balances.balances')"
      :balances="manualBalances"
      :loading="loading"
      @edit="edit($event)"
      @refresh="refresh()"
    />
    <manual-balance-table
      v-intersect="{
        handler: observers.liability,
        options: {
          threshold
        }
      }"
      data-cy="manual-liabilities"
      :title="t('manual_balances.liabilities')"
      class="mt-8"
      :balances="manualLiabilities"
      :loading="loading"
      @edit="edit($event)"
      @refresh="refresh()"
    />
    <big-dialog
      :display="openDialog"
      :title="dialogTitle"
      :subtitle="dialogSubtitle"
      :loading="submitting"
      :primary-action="t('common.actions.save')"
      @confirm="trySubmit()"
      @cancel="cancelForm()"
    >
      <manual-balances-form :edit="balanceToEdit" :context="context" />
    </big-dialog>
  </fragment>
</template>
