<script setup lang="ts">
const { email, isFormValid = false } = defineProps<{
  email: string;
  isFormValid?: boolean;
}>();

const emit = defineEmits<{
  'submit-email': [];
  'copy-email': [];
  'open-gmail': [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex">
    <RuiButton
      variant="outlined"
      color="primary"
      size="lg"
      class="!rounded-r-none !border-r-0"
      :disabled="!isFormValid"
      data-testid="submit-email"
      @click="emit('submit-email')"
    >
      <template #prepend>
        <RuiIcon name="lu-mail" />
      </template>
      {{ t('help_sidebar.report_issue.dialog.submit_options.email') }}
    </RuiButton>
    <RuiMenu
      :popper="{ placement: 'bottom-end' }"
      close-on-content-click
    >
      <template #activator="{ attrs }">
        <RuiButton
          variant="outlined"
          color="primary"
          size="lg"
          class="!rounded-l-none !px-2 -ml-[1px]"
          v-bind="attrs"
        >
          <RuiIcon name="lu-chevron-down" />
        </RuiButton>
      </template>
      <RuiButton
        variant="list"
        @click="emit('copy-email')"
      >
        <template #prepend>
          <RuiIcon name="lu-copy" />
        </template>
        {{ t('help_sidebar.report_issue.dialog.submit_options.copy_email', { email }) }}
      </RuiButton>
      <RuiButton
        variant="list"
        :disabled="!isFormValid"
        @click="emit('open-gmail')"
      >
        <template #prepend>
          <RuiIcon name="lu-mail" />
        </template>
        {{ t('help_sidebar.report_issue.dialog.submit_options.open_gmail') }}
      </RuiButton>
    </RuiMenu>
  </div>
</template>
