<script setup lang="ts">
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import type { Filters } from '@/modules/settings/accounting/rule/accounting-rule-filter-keys';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import { CustomRuleHandling } from '@/modules/settings/accounting/rule/accounting-rule-query';

/** Which half of the rules the table shows: the regular ones, or the event-specific ones. */
const customRuleHandling = defineModel<CustomRuleHandling>('customRuleHandling', { required: true });

/** The filter is a v-model rather than a prop pair so the bar writes straight back to the table. */
const filter = defineModel<Filters>('filter', { required: true });

/**
 * The fields come from the table rather than being built here: the table reads the url shape of
 * its filter bag off them, so both halves have to be looking at the same list.
 */
const { fields, loading = false } = defineProps<{
  fields: FieldDef[];
  loading?: boolean;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const pillLabels = usePillBarLabels();
</script>

<template>
  <div class="flex flex-1 flex-wrap gap-3 items-center">
    <RuiTabs
      v-model="customRuleHandling"
      variant="segmented"
      color="primary"
    >
      <RuiTab
        :value="CustomRuleHandling.EXCLUDE"
        data-testid="accounting-rule-tab-regular"
      >
        {{ t('accounting_settings.rule.tabs.regular') }}
      </RuiTab>
      <RuiTab
        :value="CustomRuleHandling.ONLY"
        data-testid="accounting-rule-tab-custom"
      >
        {{ t('accounting_settings.rule.tabs.custom') }}
      </RuiTab>
    </RuiTabs>

    <PillFilterBar
      v-model:matches="filter"
      class="flex-1 min-w-48 md:min-w-80"
      :fields="fields"
      :labels="pillLabels"
    />

    <RuiTooltip :open-delay="400">
      <template #activator>
        <RuiButton
          variant="text"
          icon
          size="sm"
          :loading="loading"
          :aria-label="t('accounting_settings.rule.refresh_tooltip')"
          data-testid="accounting-rule-refresh"
          @click="emit('refresh')"
        >
          <RuiIcon
            name="lu-refresh-ccw"
            size="18"
          />
        </RuiButton>
      </template>
      {{ t('accounting_settings.rule.refresh_tooltip') }}
    </RuiTooltip>
  </div>
</template>
