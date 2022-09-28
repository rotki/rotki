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
        <copy-button
          :tooltip="tc('error_screen.copy_tooltip')"
          :value="errorText"
        />
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
    <slot name="bottom" />
  </div>
</template>

<script setup lang="ts">
import CopyButton from '@/components/helper/CopyButton.vue';

const props = defineProps({
  header: { required: false, type: String, default: '' },
  title: { required: false, type: String, default: '' },
  subtitle: { required: false, type: String, default: '' },
  message: { required: false, type: String, default: '' },
  error: { required: false, type: String, default: '' },
  alternative: { required: false, type: String, default: '' }
});

const { error, message } = toRefs(props);

const { tc } = useI18n();

const errorText = computed(() => {
  const errorText = get(error);
  const errorMessage = get(message);
  return !errorText ? errorMessage : `${errorMessage}\n\n${errorText}`;
});
</script>

<style scoped lang="scss">
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
