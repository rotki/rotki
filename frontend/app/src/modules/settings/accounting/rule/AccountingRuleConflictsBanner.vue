<script setup lang="ts">
import AccountingRuleConflictsDialog from '@/modules/settings/accounting/rule/AccountingRuleConflictsDialog.vue';

const open = defineModel<boolean>('open', { required: true });

/** How many rules conflict. Zero draws nothing: there is nothing to warn about or resolve. */
const { count } = defineProps<{
  count: number;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <template v-if="count > 0">
    <RuiButton
      color="warning"
      class="mb-4"
      data-testid="accounting-rule-conflicts"
      @click="open = true"
    >
      <template #prepend>
        <RuiIcon name="lu-circle-alert" />
      </template>
      {{ t('accounting_settings.rule.conflicts.title') }}
      <template #append>
        <RuiChip
          size="sm"
          class="!p-0 !bg-rui-warning-darker"
          color="warning"
        >
          {{ count }}
        </RuiChip>
      </template>
    </RuiButton>
    <AccountingRuleConflictsDialog
      v-if="open"
      @close="open = false"
      @refresh="emit('refresh')"
    />
  </template>
</template>
