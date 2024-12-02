<script setup lang="ts">
import { BalanceSource } from '@/types/settings/frontend-settings';
import { TaskType } from '@/types/task-type';

const props = defineProps<{
  source: BalanceSource;
}>();

const { t } = useI18n();

const open = ref<boolean>(false);
const hide = ref<boolean>(false);
const hideBelow = ref<string>('1');
const applyToAllBalances = ref<boolean>(true);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const frontendStore = useFrontendSettingsStore();
const { balanceUsdValueThreshold } = storeToRefs(frontendStore);

const { isTaskRunning } = useTaskStore();
const isManualBalancesLoading = isTaskRunning(TaskType.MANUAL_BALANCES);
const isExchangeLoading = isTaskRunning(TaskType.QUERY_EXCHANGE_BALANCES);
const isQueryingBlockchain = isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES);

const loading = computed(() => {
  const loadingStates = {
    [BalanceSource.MANUAL]: get(isManualBalancesLoading),
    [BalanceSource.EXCHANGES]: get(isExchangeLoading),
    [BalanceSource.BLOCKCHAIN]: get(isQueryingBlockchain),
  };

  return get(applyToAllBalances)
    ? Object.values(loadingStates).some(Boolean)
    : loadingStates[props.source];
});

function applyChanges() {
  const usedNumber = get(hide) ? get(hideBelow) : '0';
  let newState: Record<BalanceSource, string>;

  if (get(applyToAllBalances)) {
    newState = {
      [BalanceSource.BLOCKCHAIN]: usedNumber,
      [BalanceSource.EXCHANGES]: usedNumber,
      [BalanceSource.MANUAL]: usedNumber,
    };
  }
  else {
    newState = {
      ...get(balanceUsdValueThreshold),
      [props.source]: usedNumber,
    };
  }

  frontendStore.updateSetting({ balanceUsdValueThreshold: newState });
}

watchImmediate([balanceUsdValueThreshold, open], ([balanceUsdValueThreshold]) => {
  const data = balanceUsdValueThreshold[props.source];

  if (data && parseFloat(data) > 0) {
    set(hide, true);
    set(hideBelow, data);
  }
  else {
    set(hide, false);
    set(hideBelow, '1');
  }
});
</script>

<template>
  <RuiMenu v-model="open">
    <template #activator="{ attrs }">
      <RuiButton
        v-bind="attrs"
        icon
        variant="text"
      >
        <RuiIcon
          color="primary"
          name="settings-4-line"
        />
      </RuiButton>
    </template>
    <div class="p-3 pt-4 flex flex-col gap-3">
      <RuiSwitch
        v-model="hide"
        class="mb-2"
        size="sm"
        :label="t('hide_small_balances.hide')"
        hide-details
        color="primary"
      />
      <RuiTextField
        v-model="hideBelow"
        :label="t('hide_small_balances.hide_under')"
        variant="outlined"
        color="primary"
        min="0"
        step="0.1"
        :disabled="!hide"
        type="number"
        hide-details
        dense
      >
        <template #prepend>
          {{ t('hide_small_balances.lt') }}
        </template>
        <template #append>
          {{ currencySymbol }}
        </template>
      </RuiTextField>
      <div class="flex gap-2 items-center">
        <RuiCheckbox
          v-model="applyToAllBalances"
          hide-details
          :disabled="loading"
          color="primary"
          :label="t('hide_small_balances.apply_to_all')"
        />
        <HintMenuIcon>
          <div class="text-sm max-w-32">
            {{ t('hide_small_balances.apply_to_all_hint') }}
          </div>
        </HintMenuIcon>
      </div>
      <div class="flex justify-end mt-4">
        <RuiButton
          :loading="loading"
          color="primary"
          @click="applyChanges()"
        >
          {{ t('hide_small_balances.apply_changes') }}
        </RuiButton>
      </div>
    </div>
  </RuiMenu>
</template>
