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
  <RuiTooltip
    :open-delay="400"
    :close-delay="0"
    :text="t('login.custom_backend.tooltip')"
  >
    <template #activator>
      <RuiButton
        :disabled="loading"
        variant="text"
        type="button"
        icon
        @click="emit('toggle')"
      >
        <RuiIcon
          name="lu-server"
          :color="color"
        />
        <template #append>
          <RuiIcon
            size="16"
            class="-ml-2"
            :name="open ? 'lu-chevron-up' : 'lu-chevron-down'"
          />
        </template>
      </RuiButton>
    </template>
  </RuiTooltip>
</template>
