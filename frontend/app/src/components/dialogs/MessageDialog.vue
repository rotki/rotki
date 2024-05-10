<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    title: string;
    message: string;
    success?: boolean;
  }>(),
  {
    success: false,
  },
);

const emit = defineEmits<{
  (e: 'dismiss'): void;
}>();

const { t } = useI18n();

const { message, success } = toRefs(props);
const visible = ref<boolean>(false);

watch(message, (message) => {
  set(visible, message.length > 0);
});

const icon = computed<string>(() =>
  get(success) ? 'checkbox-circle-line' : 'error-warning-line',
);
</script>

<template>
  <RuiDialog
    :value="visible"
    max-width="500"
    persistent
    @close="emit('dismiss')"
    @keydown.esc="emit('dismiss')"
    @keydown.enter="emit('dismiss')"
  >
    <AppBridge>
      <RuiCard>
        <template #header>
          <h5
            :class="success ? 'text-rui-success' : 'text-rui-error'"
            class="text-h5"
          >
            {{ title }}
          </h5>
        </template>

        <div class="flex flex-row items-center gap-2">
          <div>
            <RuiIcon
              size="40"
              :name="icon"
              :class="success ? 'text-rui-success' : 'text-rui-error'"
            />
          </div>
          <div
            class="hyphens-auto break-words"
            data-cy="message-dialog__title"
          >
            {{ message }}
          </div>
        </div>

        <template #footer>
          <div class="grow" />
          <RuiButton
            data-cy="message-dialog__ok"
            :color="success ? 'success' : 'error'"
            @click="emit('dismiss')"
          >
            {{ t('common.actions.ok') }}
          </RuiButton>
        </template>
      </RuiCard>
    </AppBridge>
  </RuiDialog>
</template>
