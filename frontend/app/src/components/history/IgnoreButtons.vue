<script setup lang="ts">
withDefaults(defineProps<{ disabled?: boolean }>(), { disabled: false });

const emit = defineEmits<{ (e: 'ignore', ignored: boolean): void }>();

const { t } = useI18n();
</script>

<template>
  <div class="flex flex-row gap-2">
    <RuiTooltip :popper="{ placement: 'top' }" :open-delay="400">
      <template #activator>
        <RuiButton
          class="min-w-[90px]"
          variant="outlined"
          :disabled="disabled"
          @click="emit('ignore', true)"
        >
          {{ t('ignore_buttons.ignore') }}
        </RuiButton>
      </template>
      <span>{{ t('ignore_buttons.ignore_tooltip') }}</span>
    </RuiTooltip>
    <RuiTooltip :popper="{ placement: 'top' }" :open-delay="400">
      <template #activator>
        <RuiButton
          class="min-w-[90px]"
          variant="outlined"
          :disabled="disabled"
          @click="emit('ignore', false)"
        >
          {{ t('ignore_buttons.unignore') }}
        </RuiButton>
      </template>
      <span>{{ t('ignore_buttons.unignore_tooltip') }}</span>
    </RuiTooltip>
  </div>
</template>
