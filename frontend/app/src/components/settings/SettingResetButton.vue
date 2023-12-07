<script setup lang="ts">
const emit = defineEmits<{ (e: 'click'): void }>();
const { t } = useI18n();
</script>

<template>
  <div class="mt-n2">
    <RuiTooltip
      :popper="{ placement: 'top' }"
      :open-delay="400"
      tooltip-class="max-w-[12rem]"
    >
      <template #activator>
        <RuiButton variant="text" icon @click="emit('click')">
          <RuiIcon name="loop-left-line" />
        </RuiButton>
      </template>
      <span>{{ t('backend_settings.actions.reset') }}</span>
    </RuiTooltip>
  </div>
</template>
