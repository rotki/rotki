<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <div class="px-6 py-4 text-h2 font-weight-black white--text primary">
    <div>{{ t('app.name') }}</div>
    <div class="text-caption">
      {{ t('app.moto') }}
    </div>
  </div>
</template>
