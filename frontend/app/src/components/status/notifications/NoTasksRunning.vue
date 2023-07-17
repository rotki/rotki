<script setup lang="ts">
const { t } = useI18n();
const css = useCssModule();
</script>

<template>
  <Card outlined :class="css.card">
    <VRow no-gutters align="center">
      <VCol cols="auto">
        <VIcon color="success">mdi-check-circle</VIcon>
      </VCol>
      <VCol>
        <div :class="css.title" class="text--primary">
          {{ t('no_task_running.description') }}
        </div>
      </VCol>
    </VRow>
  </Card>
</template>

<style module lang="scss">
.card {
  font-size: 16px;
  margin-left: 8px;
  margin-bottom: 8px;
}

.title {
  font-size: 1rem;
  padding-left: 1.4rem;
}
</style>
