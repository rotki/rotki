<template>
  <error-screen
    class="start-error-screen"
    :header="$t('error_screen.start_failure')"
    :title="$t('error_screen.backend_error')"
    :subtitle="$t('error_screen.message')"
    :message="message"
  >
    <v-btn
      depressed
      color="primary"
      @click="terminate()"
      v-text="$t('error_screen.terminate')"
    />
  </error-screen>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import ErrorScreen from '@/components/error/ErrorScreen.vue';

@Component({
  components: { ErrorScreen }
})
export default class StartupErrorScreen extends Vue {
  @Prop({ required: true, type: String })
  message!: string;

  terminate() {
    this.$interop.closeApp();
  }

  copy() {
    const copy = this.$refs.copy as HTMLTextAreaElement;
    copy.focus();
    copy.select();
    document.execCommand('copy');
    copy.blur();
  }
}
</script>

<style scoped lang="scss">
@import '~@/scss/scroll';

.startup-error-screen {
  background-color: white;
}
</style>
