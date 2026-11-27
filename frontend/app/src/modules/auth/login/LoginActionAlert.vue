<script setup lang="ts">
import { RuiAlert, RuiButton, type RuiIcons } from '@rotki/ui-library';
import { useI18n } from 'vue-i18n';

defineProps<{
  icon: RuiIcons;
}>();

const emit = defineEmits<{
  confirm: [];
  cancel: [];
}>();

defineSlots<{
  title: () => any;
  default: () => any;
  cancel: () => any;
  confirm: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiAlert
    class="mt-6"
    type="warning"
    :icon="icon"
  >
    <template #title>
      <span class="font-medium">
        <slot name="title" />
      </span>
    </template>
    <div class="mt-1 text-body-2 text-pretty flex flex-col gap-2">
      <slot />
    </div>

    <div class="mt-3 flex flex-wrap gap-2">
      <RuiButton
        color="primary"
        data-testid="login-action-confirm"
        @click="emit('confirm')"
      >
        <slot
          v-if="$slots.confirm"
          name="confirm"
        />
        <span v-else> {{ t('common.actions.yes') }} </span>
      </RuiButton>
      <RuiButton
        variant="outlined"
        color="primary"
        data-testid="login-action-cancel"
        @click="emit('cancel')"
      >
        <slot
          v-if="$slots.cancel"
          name="cancel"
        />
        <span v-else> {{ t('common.actions.no') }} </span>
      </RuiButton>
    </div>
  </RuiAlert>
</template>
