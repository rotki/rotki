<template>
  <div class="error-screen">
    <div>
      <v-icon size="120" color="error">mdi-alert-circle</v-icon>
    </div>
    <div v-if="header" class="error-screen__title">
      <div class="text-h1">
        {{ header }}
      </div>
    </div>

    <slot />

    <v-card v-if="!alternative" outlined class="error-screen__message mt-3">
      <v-card-title>
        {{ title }}
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
      <v-card-subtitle>
        {{ subtitle }}
      </v-card-subtitle>
      <v-card-text class="font-weight-light error-screen__description">
        <pre
          class="font-weight-regular text-caption text-wrap error-screen__description__message"
        >
          {{ message }}
          <v-divider v-if="error" class="mt-4 mb-2"/>
          {{ error }}
        </pre>
        <textarea
          ref="copy"
          v-model="errorText"
          class="error-screen__copy-area"
        />
      </v-card-text>
    </v-card>
    <div v-else class="text-h5 mt-12">{{ alternative }}</div>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class ErrorScreen extends Vue {
  @Prop({ required: false, type: String, default: '' })
  header!: string;
  @Prop({ required: false, type: String, default: '' })
  title!: string;
  @Prop({ required: false, type: String, default: '' })
  subtitle!: string;
  @Prop({ required: false, type: String, default: '' })
  message!: string;
  @Prop({ required: false, type: String, default: '' })
  error!: string;
  @Prop({ required: false, type: String, default: '' })
  alternative!: string;

  get errorText(): string {
    if (!this.error) {
      return this.message;
    }
    return this.message + '\n\n' + this.error;
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

    &__message {
      max-width: 500px;
      width: 100%;
    }
  }
}
</style>
