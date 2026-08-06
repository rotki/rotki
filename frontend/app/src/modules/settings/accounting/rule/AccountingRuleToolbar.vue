<script setup lang="ts">
import type { Filters, Matcher } from '@/modules/core/table/filters/use-accounting-rule-filter';
import { usePillBarLabels } from '@/modules/core/table/pill/composables/use-pill-bar-labels';
import PillFilterBar from '@/modules/core/table/pill/PillFilterBar.vue';
import { CustomRuleHandling } from '@/modules/settings/accounting/rule/accounting-rule-query';
import { useAccountingRuleFields } from '@/modules/settings/accounting/rule/use-accounting-rule-fields';

/** Which half of the rules the table shows: the regular ones, or the event-specific ones. */
const customRuleHandling = defineModel<CustomRuleHandling>('customRuleHandling', { required: true });
/** The filter is a v-model rather than a prop pair so the bar writes straight back to the table. */
const filter = defineModel<Filters>('filter', { required: true });

const { matchers } = defineProps<{
  matchers: Matcher[];
}>();

const { t } = useI18n({ useScope: 'global' });

const fields = useAccountingRuleFields(() => matchers);
const pillLabels = usePillBarLabels();
</script>

<template>
  <div class="flex flex-wrap gap-x-4 gap-y-2 items-center justify-between">
    <RuiTabs
      v-model="customRuleHandling"
      color="primary"
      class="border border-default rounded bg-white dark:bg-rui-grey-900 flex max-w-min"
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
      class="flex-1 min-w-[12rem] md:min-w-[20rem]"
      :fields="fields"
      :labels="pillLabels"
    />
  </div>
</template>
