<script setup lang="ts">
withDefaults(
  defineProps<{
    disabled?: boolean;
    disabledActions?: { ignore?: boolean; unIgnore?: boolean };
  }>(),
  { disabled: false, disabledActions: undefined },
);

const emit = defineEmits<{ (e: 'ignore', ignored: boolean): void }>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex flex-row gap-2">
    <RuiTooltip
      :popper="{ placement: 'top' }"
      :open-delay="400"
    >
      <template #activator>
        <RuiButton
          class="min-w-[5.625rem]"
          variant="outlined"
          :disabled="disabled || disabledActions?.ignore"
          @click="emit('ignore', true)"
        >
          {{ t('ignore_buttons.ignore') }}
        </RuiButton>
      </template>
      <span>{{ t('ignore_buttons.ignore_tooltip') }}</span>
    </RuiTooltip>
    <RuiTooltip
      :popper="{ placement: 'top' }"
      :open-delay="400"
    >
      <template #activator>
        <RuiButton
          class="min-w-[5.625rem]"
          variant="outlined"
          :disabled="disabled || disabledActions?.unIgnore"
          @click="emit('ignore', false)"
        >
          {{ t('ignore_buttons.unignore') }}
        </RuiButton>
      </template>
      <span>{{ t('ignore_buttons.unignore_tooltip') }}</span>
    </RuiTooltip>
  </div>
</template>
