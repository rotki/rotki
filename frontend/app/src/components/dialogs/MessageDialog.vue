<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';

const props = withDefaults(defineProps<{
  title: string;
  message: string;
  success?: boolean;
}>(), {
  success: false,
});

const emit = defineEmits<{
  dismiss: [];
}>();

const { message, success } = toRefs(props);

const { t } = useI18n();

const visible = ref<boolean>(false);

const icon = computed<RuiIcons>(() => (get(success) ? 'checkbox-circle-line' : 'error-warning-line'));

watch(message, (message) => {
  set(visible, message.length > 0);
});
</script>

<template>
  <RuiDialog
    :model-value="visible"
    max-width="500"
    persistent
    z-index="10000"
    @close="emit('dismiss')"
    @keydown.esc="emit('dismiss')"
    @keydown.enter="emit('dismiss')"
  >
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
  </RuiDialog>
</template>
