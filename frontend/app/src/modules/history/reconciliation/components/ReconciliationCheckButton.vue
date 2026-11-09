<script setup lang="ts">
const { detecting = false, disabled = false, disabledReason } = defineProps<{
  detecting?: boolean;
  disabled?: boolean;
  disabledReason?: string;
}>();

const emit = defineEmits<{
  check: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiTooltip
    v-if="disabledReason"
    :open-delay="300"
  >
    <template #activator>
      <span>
        <RuiButton
          color="primary"
          :loading="detecting"
          :disabled="disabled"
          data-testid="reconciliation-check-now"
          @click="emit('check')"
        >
          <template #prepend>
            <RuiIcon name="lu-scale" />
          </template>
          {{ t('data_issues.reconciliation.check.action') }}
        </RuiButton>
      </span>
    </template>
    {{ disabledReason }}
  </RuiTooltip>
  <RuiButton
    v-else
    color="primary"
    :loading="detecting"
    :disabled="disabled"
    data-testid="reconciliation-check-now"
    @click="emit('check')"
  >
    <template #prepend>
      <RuiIcon name="lu-scale" />
    </template>
    {{ t('data_issues.reconciliation.check.action') }}
  </RuiButton>
</template>
