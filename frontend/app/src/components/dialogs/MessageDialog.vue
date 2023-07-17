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

const icon = computed<string>(() =>
  get(success) ? 'mdi-check-circle ' : 'mdi-alert-circle'
);

const dismiss = () => emit('dismiss');

const { t } = useI18n();
</script>

<template>
  <div>
    <VDialog
      :value="visible"
      max-width="500"
      class="message-dialog"
      persistent
      @close="dismiss()"
      @keydown.esc="dismiss()"
      @keydown.enter="dismiss()"
    >
      <VCard>
        <VCardTitle
          :class="{ 'green--text': success, 'red--text': !success }"
          class="text-h5 message-dialog__title"
        >
          {{ title }}
        </VCardTitle>
        <VRow align="center" class="mx-0 message-dialog__body">
          <VCol cols="1">
            <VIcon
              size="40"
              class="dialog-icon"
              :class="{ 'green--text': success, 'red--text': !success }"
            >
              {{ icon }}
            </VIcon>
          </VCol>
          <VCol cols="11">
            <VCardText class="message-dialog__message">
              {{ message }}
            </VCardText>
          </VCol>
        </VRow>

        <VCardActions>
          <VSpacer />
          <VBtn
            :color="success ? 'green' : 'red'"
            text
            class="message-dialog__buttons__confirm"
            @click="dismiss()"
          >
            {{ t('common.actions.ok') }}
          </VBtn>
        </VCardActions>
      </VCard>
    </VDialog>
  </div>
</template>

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
