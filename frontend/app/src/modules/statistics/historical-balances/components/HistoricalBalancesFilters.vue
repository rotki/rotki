<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import { historicalBalancesParams } from '@/modules/statistics/historical-balances/historical-balances-fields';
import { HistoricalBalancesMode } from '@/modules/statistics/historical-balances/historical-balances-view';
import { useHistoricalBalancesFields } from '@/modules/statistics/historical-balances/use-historical-balances-fields';

const selectedLocations = defineModel<string[]>('locations', { required: true });
const selectedAccounts = defineModel<string[]>('accounts', { required: true });
const search = defineModel<string>('search', { required: true });
const mode = defineModel<HistoricalBalancesMode>('mode', { required: true });

const { accountOptions, locationOptions } = defineProps<{
  locationOptions: string[];
  accountOptions: string[];
}>();

const { t } = useI18n({ useScope: 'global' });

const fields = useHistoricalBalancesFields(() => locationOptions, () => accountOptions);
const pillLabels = usePillBarLabels();

/** Written through by the bar, but owned by the page, which filters the day's balances by them. */
const params = historicalBalancesParams(selectedLocations, selectedAccounts, search);

const modes = computed<{ value: HistoricalBalancesMode; label: string; icon: RuiIcons }[]>(() => [
  { icon: 'lu-layers', label: t('historical_balances.mode.collection'), value: HistoricalBalancesMode.COLLECTION },
  { icon: 'lu-list', label: t('historical_balances.mode.flat'), value: HistoricalBalancesMode.FLAT },
]);
</script>

<template>
  <div class="flex flex-wrap items-start gap-3">
    <PillFilterBar
      v-model:params="params"
      class="grow min-w-0"
      :fields="fields"
      :labels="pillLabels"
      data-testid="historical-balances-filter"
    />
    <RuiButtonGroup
      v-model="mode"
      variant="outlined"
      color="primary"
      active-color="primary"
      required
      data-testid="historical-balances-mode"
    >
      <RuiButton
        v-for="option in modes"
        :key="option.value"
        :model-value="option.value"
        :data-testid="`historical-balances-mode-${option.value}`"
      >
        <template #prepend>
          <RuiIcon
            :name="option.icon"
            size="16"
          />
        </template>
        {{ option.label }}
      </RuiButton>
    </RuiButtonGroup>
  </div>
</template>
