<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { minValue, required } from '@vuelidate/validators';
import { omit } from 'es-toolkit';
import HintMenuIcon from '@/components/HintMenuIcon.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useTaskStore } from '@/store/tasks';
import { BalanceSource, type BalanceValueThreshold } from '@/types/settings/frontend-settings';
import { TaskType } from '@/types/task-type';
import { toMessages } from '@/utils/validation';

const props = defineProps<{
  source: BalanceSource;
}>();

const { t } = useI18n({ useScope: 'global' });

const open = ref<boolean>(false);
const hide = ref<boolean>(false);
const hideBelow = ref<string>('1');
const applyToAllBalances = ref<boolean>(true);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const frontendStore = useFrontendSettingsStore();
const { balanceValueThreshold } = storeToRefs(frontendStore);

const { useIsTaskRunning } = useTaskStore();
const isManualBalancesLoading = useIsTaskRunning(TaskType.MANUAL_BALANCES);
const isExchangeLoading = useIsTaskRunning(TaskType.QUERY_EXCHANGE_BALANCES);
const isQueryingBlockchain = useIsTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES);

const v$ = useVuelidate(
  {
    hideBelow: {
      minValue: minValue(0),
      required,
    },
  },
  {
    hideBelow,
  },
  {
    $autoDirty: true,
  },
);

const loading = computed(() => {
  const loadingStates = {
    [BalanceSource.BLOCKCHAIN]: get(isQueryingBlockchain),
    [BalanceSource.EXCHANGES]: get(isExchangeLoading),
    [BalanceSource.MANUAL]: get(isManualBalancesLoading),
  };

  return get(applyToAllBalances)
    ? Object.values(loadingStates).some(Boolean)
    : loadingStates[props.source];
});

const hint = computed(() => {
  if (get(hideBelow) !== '0') {
    return t('hide_small_balances.hint', {
      symbol: get(currencySymbol),
      value: get(hideBelow),
    });
  }
  return t('hide_small_balances.hint_zero');
});

async function applyChanges(): Promise<void> {
  if (!(await get(v$).$validate())) {
    return;
  }
  const usedNumber = get(hide) ? get(hideBelow) : undefined;
  let newState: BalanceValueThreshold;

  if (get(applyToAllBalances)) {
    newState = usedNumber
      ? {
          [BalanceSource.BLOCKCHAIN]: usedNumber,
          [BalanceSource.EXCHANGES]: usedNumber,
          [BalanceSource.MANUAL]: usedNumber,
        }
      : {};
  }
  else {
    newState = {
      ...omit(get(balanceValueThreshold), [props.source]),
      ...(usedNumber ? { [props.source]: usedNumber } : {}),
    };
  }

  frontendStore.updateSetting({ balanceValueThreshold: newState });
}

watchImmediate([balanceValueThreshold, open], ([balanceValueThreshold]) => {
  const data = balanceValueThreshold[props.source];

  if (data) {
    set(hide, true);
    set(hideBelow, data);
  }
  else {
    set(hide, false);
    set(hideBelow, '1');
  }
});

watch(hide, (hide) => {
  if (!hide) {
    set(hideBelow, '1');
  }
  get(v$).$reset();
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
          name="lu-settings"
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
        :hint="hint"
        :error-messages="toMessages(v$.hideBelow)"
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
