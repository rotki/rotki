<script setup lang="ts">
import type { ZodType } from 'zod';
import { useForm } from '@/modules/core/form/use-form';
import {
  DEFAULT_THRESHOLD,
  type HideSmallBalancesFormState,
  hideSmallBalancesSchema,
  toThresholds,
} from '@/modules/settings/hide-small-balances-form';
import { BalanceSource, type BalanceValueThreshold } from '@/modules/settings/types/frontend-settings';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import HintMenuIcon from '@/modules/shell/components/HintMenuIcon.vue';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

const { source } = defineProps<{
  source: BalanceSource;
}>();

const { t } = useI18n({ useScope: 'global' });

const open = ref<boolean>(false);

const currencySymbol = useSetting('currencySymbol');
const balanceValueThreshold = useSetting('balanceValueThreshold');
const { updateFrontendSetting } = useSettingsOperations();

const { useIsActive } = useTaskCenter();
const isManualBalancesLoading = useIsActive(ActivityKind.MANUAL_BALANCES);
const isExchangeLoading = useIsActive(ActivityKind.EXCHANGE_BALANCES);
const isQueryingBlockchain = useIsActive(ActivityKind.BLOCKCHAIN_BALANCES);

const schema = computed<ZodType>(() => hideSmallBalancesSchema({
  min: t('settings.validation.number.min', { min: 0 }),
  required: t('settings.validation.number.non_empty'),
}));

const form = useForm<HideSmallBalancesFormState, BalanceValueThreshold>({
  initial: (): HideSmallBalancesFormState => ({
    applyToAllBalances: true,
    hide: false,
    hideBelow: DEFAULT_THRESHOLD,
  }),
  schema,
  submit: async (payload: BalanceValueThreshold): Promise<{ success: boolean }> => {
    await updateFrontendSetting({ balanceValueThreshold: payload });
    return { success: true };
  },
  transform: (state): BalanceValueThreshold => toThresholds(state, source, get(balanceValueThreshold)),
});

const loading = computed<boolean>(() => {
  const loadingStates = {
    [BalanceSource.BLOCKCHAIN]: get(isQueryingBlockchain),
    [BalanceSource.EXCHANGES]: get(isExchangeLoading),
    [BalanceSource.MANUAL]: get(isManualBalancesLoading),
  };

  return form.state.applyToAllBalances
    ? Object.values(loadingStates).some(Boolean)
    : loadingStates[source];
});

const hint = computed<string>(() => {
  if (form.state.hideBelow !== '0') {
    return t('hide_small_balances.hint', {
      symbol: get(currencySymbol),
      value: form.state.hideBelow,
    });
  }
  return t('hide_small_balances.hint_zero');
});

watchImmediate([balanceValueThreshold, open], ([thresholds]) => {
  const threshold = thresholds[source];
  form.state.hide = Boolean(threshold);
  form.state.hideBelow = threshold ?? DEFAULT_THRESHOLD;
});

watch(() => form.state.hide, (hide) => {
  // Switching hiding off puts the field back to a value that cannot be blocking the save.
  form.reset({
    applyToAllBalances: form.state.applyToAllBalances,
    hide,
    hideBelow: hide ? form.state.hideBelow : DEFAULT_THRESHOLD,
  });
});
</script>

<template>
  <RuiMenu v-model="open">
    <template #activator="{ attrs }">
      <RuiButton
        v-bind="attrs"
        icon
        variant="text"
        size="lg"
      >
        <RuiIcon
          color="primary"
          name="lu-settings"
        />
      </RuiButton>
    </template>
    <div class="p-3 pt-4 flex flex-col gap-3">
      <RuiSwitch
        v-model="form.state.hide"
        class="mb-2"
        size="sm"
        data-testid="hide-small-balances-toggle"
        :label="t('hide_small_balances.hide')"
        hide-details
        color="primary"
      />
      <RuiTextField
        v-model="form.state.hideBelow"
        data-testid="hide-small-balances-threshold"
        :label="t('hide_small_balances.hide_under')"
        variant="outlined"
        color="primary"
        min="0"
        step="0.1"
        :disabled="!form.state.hide"
        type="number"
        :hint="hint"
        :error-messages="form.errors('hideBelow')"
        dense
        @update:model-value="form.touch('hideBelow')"
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
          v-model="form.state.applyToAllBalances"
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
          data-testid="hide-small-balances-apply"
          @click="form.submit()"
        >
          {{ t('hide_small_balances.apply_changes') }}
        </RuiButton>
      </div>
    </div>
  </RuiMenu>
</template>
