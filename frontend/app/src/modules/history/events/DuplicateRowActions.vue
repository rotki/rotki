<script setup lang="ts">
const { fixLoading, ignoreLoading, mode } = defineProps<{
  mode: 'auto-fix' | 'manual-review' | 'ignored';
  fixLoading?: boolean;
  ignoreLoading?: boolean;
}>();

const emit = defineEmits<{
  fix: [];
  ignore: [];
  restore: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex items-center gap-2">
    <RuiButton
      v-if="mode === 'auto-fix'"
      size="sm"
      color="primary"
      :loading="fixLoading"
      @click="emit('fix')"
    >
      <template #prepend>
        <RuiIcon
          size="16"
          name="lu-wand-sparkles"
        />
      </template>
      {{ t('customized_event_duplicates.actions.fix') }}
    </RuiButton>
    <RuiTooltip
      v-if="mode === 'ignored'"
      :open-delay="400"
      :popper="{ placement: 'top' }"
    >
      <template #activator>
        <RuiButton
          size="sm"
          color="primary"
          :loading="ignoreLoading"
          @click="emit('restore')"
        >
          <template #prepend>
            <RuiIcon
              size="16"
              name="lu-rotate-ccw"
            />
          </template>
          {{ t('customized_event_duplicates.actions.restore') }}
        </RuiButton>
      </template>
      {{ t('customized_event_duplicates.actions.restore_tooltip') }}
    </RuiTooltip>
    <RuiTooltip
      v-else
      :open-delay="400"
      :popper="{ placement: 'top' }"
    >
      <template #activator>
        <RuiButton
          size="sm"
          variant="outlined"
          :loading="ignoreLoading"
          @click="emit('ignore')"
        >
          <template #prepend>
            <RuiIcon
              size="16"
              name="lu-eye-off"
            />
          </template>
          {{ t('customized_event_duplicates.actions.mark_non_duplicated') }}
        </RuiButton>
      </template>
      {{ t('customized_event_duplicates.actions.mark_non_duplicated_tooltip') }}
    </RuiTooltip>
  </div>
</template>
