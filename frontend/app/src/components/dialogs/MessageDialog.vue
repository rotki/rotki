<template>
  <v-dialog v-model="visible" persistent max-width="500" class="message-dialog">
    <v-card>
      <v-card-title
        :class="{ 'green--text': success, 'red--text': !success }"
        class="text-h5 message-dialog__title"
      >
        {{ title }}
      </v-card-title>
      <v-row align="center" class="mx-0 message-dialog__body">
        <v-col cols="1">
          <v-icon
            size="40"
            class="dialog-icon"
            :class="{ 'green--text': success, 'red--text': !success }"
          >
            {{ icon }}
          </v-icon>
        </v-col>
        <v-col cols="11">
          <v-card-text class="message-dialog__message">
            {{ message }}
          </v-card-text>
        </v-col>
      </v-row>

      <v-card-actions>
        <v-spacer />
        <v-btn
          :color="success ? 'green' : 'red'"
          text
          class="message-dialog__buttons__confirm"
          @click="dismiss()"
        >
          {{ t('common.actions.ok') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
const props = defineProps({
  title: { required: true, type: String },
  message: { required: true, type: String },
  success: { required: false, type: Boolean, default: false }
});

const emit = defineEmits(['dismiss']);
const { message, success } = toRefs(props);
const visible = ref<boolean>(false);

watch(message, message => {
  set(visible, message.length > 0);
});

const icon = computed<string>(() => {
  return get(success) ? 'mdi-check-circle ' : 'mdi-alert-circle';
});

const dismiss = () => emit('dismiss');

const { t } = useI18n();
</script>

<style scoped lang="scss">
.message-dialog {
  &__message {
    overflow-wrap: break-word;
    word-wrap: break-word;
    hyphens: auto;
  }

  &__body {
    padding: 0 16px;
  }
}
</style>
