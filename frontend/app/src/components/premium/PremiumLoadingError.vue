<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <RuiAlert
    dense
    type="error"
    text
    variant="outlined"
    :title="t('premium_loading_failed.title')"
  >
    <p class="mt-1">
      {{ t('premium_loading_failed.description') }}
    </p>
    <p>{{ t('premium_loading_failed.try_again') }}</p>
    <p>{{ t('premium_loading_failed.open_issue') }}</p>
  </RuiAlert>
</template>
