<script setup lang="ts">
const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiAlert
    type="error"
    variant="outlined"
    class="!m-4"
    :title="t('premium_loading_failed.title')"
  >
    <p class="mt-1">
      {{ t('premium_loading_failed.description') }}
    </p>
    <p>{{ t('premium_loading_failed.try_again') }}</p>
    <p>{{ t('premium_loading_failed.open_issue') }}</p>
  </RuiAlert>
</template>
