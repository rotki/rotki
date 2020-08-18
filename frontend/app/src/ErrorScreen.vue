<template>
  <div class="error-screen">
    <div>
      <v-icon size="120" color="error">fa-exclamation-circle</v-icon>
    </div>
    <div class="error-screen__title">
      <h1>Rotki failed to start</h1>
    </div>

    <v-btn depressed color="primary" @click="terminate()">
      Terminate
    </v-btn>

    <v-card outlined class="error-screen__message mt-3">
      <v-card-title>
        There is a problem with the backend. <v-spacer />
        <v-tooltip top="">
          <template #activator="{ on, attrs }">
            <v-btn v-bind="attrs" icon v-on="on" @click="copy()">
              <v-icon>fa-copy</v-icon>
            </v-btn>
          </template>
          <span>Copy the error text to the clipboard</span>
        </v-tooltip>
      </v-card-title>
      <v-card-subtitle>
        Open an issue in Github and include rotki_electron.log and
        rotkehlchen.log. The backend's output follows below:
      </v-card-subtitle>
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
@import '@/scss/scroll';

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
    margin-bottom: 5px;
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
