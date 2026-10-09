<script setup lang="ts">
import type { ServerColor } from '@/modules/auth/login/use-custom-backend';

const { color, loading, open } = defineProps<{
  open: boolean;
  loading: boolean;
  color?: ServerColor;
}>();

const emit = defineEmits<{
  toggle: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <!-- labelled rather than a bare icon, which read as a stray element under the form -->
  <RuiTooltip
    :open-delay="400"
    :close-delay="0"
    :text="t('login.custom_backend.tooltip')"
  >
    <template #activator>
      <RuiButton
        :disabled="loading"
        variant="text"
        size="sm"
        type="button"
        class="-ms-1.5"
        :aria-expanded="open"
        @click="emit('toggle')"
      >
        <template #prepend>
          <RuiIcon
            name="lu-server"
            size="16"
            :color="color"
          />
        </template>
        {{ t('login.custom_backend.toggle') }}
        <template #append>
          <RuiIcon
            size="14"
            :name="open ? 'lu-chevron-up' : 'lu-chevron-down'"
          />
        </template>
      </RuiButton>
    </template>
  </RuiTooltip>
</template>
