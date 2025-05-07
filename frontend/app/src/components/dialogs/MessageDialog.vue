<script setup lang="ts">
import type { Message } from '@rotki/common';
import type { RuiIcons } from '@rotki/ui-library';

const props = defineProps<{
  message: Message;
}>();

const emit = defineEmits<{
  dismiss: [];
}>();

const { message } = toRefs(props);

const { t } = useI18n({ useScope: 'global' });

const icon = computed<RuiIcons>(() => (get(props.message.success) ? 'lu-circle-check' : 'lu-circle-alert'));
</script>

<template>
  <RuiDialog
    :model-value="true"
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
          :class="message.success ? 'text-rui-success' : 'text-rui-error'"
          class="text-h5"
        >
          {{ message.title }}
        </h5>
      </template>

      <div class="flex flex-row items-center gap-2">
        <div>
          <RuiIcon
            size="40"
            :name="icon"
            :class="message.success ? 'text-rui-success' : 'text-rui-error'"
          />
        </div>
        <div
          class="hyphens-auto break-words"
          data-cy="message-dialog__title"
        >
          {{ message.description }}
        </div>
      </div>

      <template #footer>
        <div class="grow" />
        <RuiButton
          data-cy="message-dialog__ok"
          :color="message.success ? 'success' : 'error'"
          @click="emit('dismiss')"
        >
          {{ t('common.actions.ok') }}
        </RuiButton>
      </template>
    </RuiCard>
  </RuiDialog>
</template>
