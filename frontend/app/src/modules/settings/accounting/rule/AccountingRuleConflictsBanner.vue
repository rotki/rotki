<script setup lang="ts">
import AccountingRuleConflictsDialog from '@/modules/settings/accounting/rule/AccountingRuleConflictsDialog.vue';

const open = defineModel<boolean>('open', { required: true });

/**
 * How many rules conflict. Zero draws no button, but an `open` dialog still renders: a link asking
 * for the conflicts opens it even when counting them failed, so its table can say why.
 */
const { count } = defineProps<{
  count: number;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div
    v-if="count > 0"
    class="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-rui-control border border-rui-warning/40 bg-rui-warning/10 pl-3 pr-1 py-1 text-sm text-rui-text"
    data-testid="accounting-rule-conflicts-banner"
  >
    <RuiIcon
      name="lu-triangle-alert"
      size="16"
      class="text-rui-warning shrink-0"
    />
    <span class="flex-1">
      {{ t('accounting_settings.rule.conflicts.banner', { count }, count) }}
    </span>
    <RuiButton
      variant="text"
      color="warning"
      size="sm"
      data-testid="accounting-rule-conflicts"
      @click="open = true"
    >
      {{ t('accounting_settings.rule.conflicts.resolve') }}
    </RuiButton>
  </div>
  <AccountingRuleConflictsDialog
    v-if="open"
    @close="open = false"
    @refresh="emit('refresh')"
  />
</template>
