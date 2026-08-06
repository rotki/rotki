<script setup lang="ts">
import type { Filters, Matcher } from '@/modules/core/table/filters/use-accounting-rule-filter';
import TableFilter from '@/modules/core/table/TableFilter.vue';
import { CustomRuleHandling } from '@/modules/settings/accounting/rule/accounting-rule-query';

/** Which half of the rules the table shows: the regular ones, or the event-specific ones. */
const customRuleHandling = defineModel<CustomRuleHandling>('customRuleHandling', { required: true });

defineProps<{
  matchers: Matcher[];
  filter: Filters;
}>();

const emit = defineEmits<{
  'update:filter': [filter: Filters];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex flex-wrap gap-x-4 gap-y-2 items-center justify-between">
    <RuiTabs
      v-model="customRuleHandling"
      color="primary"
      class="border border-default rounded bg-white dark:bg-rui-grey-900 flex max-w-min"
    >
      <RuiTab :value="CustomRuleHandling.EXCLUDE">
        {{ t('accounting_settings.rule.tabs.regular') }}
      </RuiTab>
      <RuiTab :value="CustomRuleHandling.ONLY">
        {{ t('accounting_settings.rule.tabs.custom') }}
      </RuiTab>
    </RuiTabs>

    <div class="w-full md:w-[25rem] ml-auto">
      <TableFilter
        :matches="filter"
        :matchers="matchers"
        @update:matches="emit('update:filter', $event)"
      />
    </div>
  </div>
</template>
