<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <VCard>
    <VAlert color="error" icon="mdi-alert" outlined prominent>
      <span class="font-medium">
        {{ t('premium_loading_failed.title') }}
      </span>
      <p class="mt-1">
        {{ t('premium_loading_failed.description') }}
      </p>
      <p>{{ t('premium_loading_failed.try_again') }}</p>
      <p>{{ t('premium_loading_failed.open_issue') }}</p>
    </VAlert>
  </VCard>
</template>
