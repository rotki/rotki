<template>
  <v-card>
    <v-alert color="error" icon="mdi-alert" outlined prominent>
      <span class="font-weight-medium">
        {{ t('premium_loading_failed.title') }}
      </span>
      <p class="mt-1">
        {{ t('premium_loading_failed.description') }}
      </p>
      <p>{{ t('premium_loading_failed.try_again') }}</p>
      <p>{{ t('premium_loading_failed.open_issue') }}</p>
    </v-alert>
  </v-card>
</template>

<script setup lang="ts">
const { t } = useI18n();
</script>
