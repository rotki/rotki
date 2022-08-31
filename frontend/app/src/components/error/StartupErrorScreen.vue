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

<script lang="ts">
import { useClipboard } from '@vueuse/core';
import { defineComponent, toRefs } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import ErrorScreen from '@/components/error/ErrorScreen.vue';

import { interop } from '@/electron-interop';

export default defineComponent({
  name: 'StartupErrorScreen',
  components: { ErrorScreen },
  props: {
    message: { required: true, type: String }
  },
  setup(props) {
    const { message } = toRefs(props);
    const { tc } = useI18n();

    const terminate = () => {
      interop.closeApp();
    };

    const { copy: copyText } = useClipboard({ source: message });

    const copy = () => copyText();

    return {
      terminate,
      copy,
      tc
    };
  }
});
</script>

<style scoped lang="scss">
.startup-error-screen {
  background-color: white;
}
</style>
