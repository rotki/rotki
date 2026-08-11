<script setup lang="ts">
const { primary, hasErrors = false, actionDisabled = false, loading = false, errorCount = 0 } = defineProps<{
  primary: string;
  hasErrors?: boolean;
  actionDisabled?: boolean;
  loading?: boolean;
  errorCount?: number;
}>();
</script>

<template>
  <RuiButton
    data-testid="confirm"
    :color="hasErrors ? 'error' : 'primary'"
    :disabled="actionDisabled || loading"
    :loading="loading"
    type="submit"
  >
    {{ primary }}
    <template
      v-if="hasErrors"
      #append
    >
      <RuiChip
        size="sm"
        class="!py-0 !px-0.5 !bg-rui-error-darker"
        color="error"
      >
        {{ errorCount }}
      </RuiChip>
    </template>
  </RuiButton>
</template>
