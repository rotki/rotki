<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';

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

const { t } = useI18n();
</script>

<template>
  <RuiAlert
    class="mt-8"
    type="warning"
    :icon="icon"
  >
    <template #title>
      <slot name="title" />
    </template>
    <slot />

    <div class="mt-4 flex justify-end gap-3">
      <RuiButton
        variant="text"
        color="primary"
        @click="emit('cancel')"
      >
        <slot
          v-if="$slots.cancel"
          name="cancel"
        />
        <span v-else> {{ t('common.actions.no') }} </span>
      </RuiButton>
      <RuiButton
        color="primary"
        @click="emit('confirm')"
      >
        <slot
          v-if="$slots.confirm"
          name="confirm"
        />
        <span v-else> {{ t('common.actions.yes') }} </span>
      </RuiButton>
    </div>
  </RuiAlert>
</template>
