<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <div class="pa-6 text-h2 font-weight-black white--text primary">
    <div>{{ t('app.name') }}</div>
    <div class="text-caption">
      {{ t('app.moto') }}
    </div>
  </div>
</template>
