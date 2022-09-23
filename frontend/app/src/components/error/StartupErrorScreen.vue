<template>
  <error-screen
    class="start-error-screen"
    :header="tc('error_screen.start_failure')"
    :title="tc('error_screen.backend_error')"
    :subtitle="tc('error_screen.message')"
    :message="message"
  >
    <v-btn depressed color="primary" @click="terminate()">
      {{ tc('common.actions.terminate') }}
    </v-btn>
  </error-screen>
</template>

<script setup lang="ts">
import ErrorScreen from '@/components/error/ErrorScreen.vue';
import { interop } from '@/electron-interop';

const props = defineProps({
  message: { required: true, type: String }
});

const { message } = toRefs(props);
const { tc } = useI18n();

const terminate = () => {
  interop.closeApp();
};
</script>

<style scoped lang="scss">
.startup-error-screen {
  background-color: white;
}
</style>
