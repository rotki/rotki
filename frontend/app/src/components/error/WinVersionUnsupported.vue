<script setup lang="ts">
const { t } = useI18n();
const { closeApp } = useInterop();
</script>

<template>
  <ErrorScreen
    class="win-unsupported"
    :header="t('win_unsupported.header')"
    :alternative="t('win_unsupported.message')"
  >
    <RuiButton depressed color="primary" @click="closeApp()">
      {{ t('common.actions.terminate') }}
    </RuiButton>
  </ErrorScreen>
</template>

<style scoped lang="scss">
.win-unsupported {
  padding: 2rem 0;
  background-color: white;
}
</style>
