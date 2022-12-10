<template>
  <error-screen
    :class="css.overlay"
    :header="tc('error_screen.start_failure')"
    :title="tc('error_screen.backend_error')"
    :subtitle="tc('error_screen.message')"
    :message="message"
  >
    <v-btn depressed color="primary" @click="closeApp()">
      {{ tc('common.actions.terminate') }}
    </v-btn>
  </error-screen>
</template>

<script setup lang="ts">
import ErrorScreen from '@/components/error/ErrorScreen.vue';

defineProps({
  message: { required: true, type: String }
});

const { tc } = useI18n();
const css = useCssModule();
const { closeApp } = useInterop();
</script>

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
