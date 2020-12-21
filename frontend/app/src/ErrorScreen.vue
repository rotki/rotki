<template>
  <div class="error-screen">
    <div>
      <v-icon size="120" color="error">mdi-alert-circle</v-icon>
    </div>
    <div class="error-screen__title">
      <div class="text-h1" v-text="$t('error_screen.start_failure')" />
    </div>

    <v-btn
      depressed
      color="primary"
      @click="terminate()"
      v-text="$t('error_screen.terminate')"
    />

    <v-card outlined class="error-screen__message mt-3">
      <v-card-title>
        <span v-text="$t('error_screen.backend_error')" />
        <v-spacer />
        <v-tooltip top>
          <template #activator="{ on, attrs }">
            <v-btn v-bind="attrs" icon v-on="on" @click="copy()">
              <v-icon>mdi-content-copy</v-icon>
            </v-btn>
          </template>
          <span v-text="$t('error_screen.copy_tooltip')" />
        </v-tooltip>
      </v-card-title>
      <v-card-subtitle v-text="$t('error_screen.message')" />
      <v-card-text class="font-weight-light error-screen__description">
        <pre class="font-weight-regular text-caption">{{ message }}</pre>
        <textarea
          ref="copy"
          v-model="message"
          class="error-screen__copy-area"
        />
      </v-card-text>
    </v-card>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class ErrorScreen extends Vue {
  @Prop({ required: true })
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

.error-screen {
  background-color: white;
  height: 100%;
  width: 100%;
  z-index: 99999;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;

  &__message {
    max-width: 80%;
  }

  &__title {
    margin-top: 25px;
    margin-bottom: 20px;
  }

  &__copy-area {
    position: absolute;
    top: -999em;
    left: -999em;
  }

  &__description {
    height: 300px;
    overflow: auto;
  }
}
</style>
