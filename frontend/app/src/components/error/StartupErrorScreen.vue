<script setup lang="ts">
defineProps({
  message: { required: true, type: String }
});

const { t } = useI18n();
const css = useCssModule();
const { closeApp } = useInterop();
</script>

<template>
  <ErrorScreen
    :class="css.overlay"
    :header="t('error_screen.start_failure')"
    :title="t('error_screen.backend_error')"
    :subtitle="t('error_screen.message')"
    :message="message"
  >
    <RuiButton variant="default" color="primary" @click="closeApp()">
      {{ t('common.actions.terminate') }}
    </RuiButton>
  </ErrorScreen>
</template>

<style module lang="scss">
.overlay {
  background-color: #fafafa;
  height: 100vh !important;
  width: 100vw !important;
  position: fixed;
  top: 0;
  left: 0;
}
</style>
