<script lang="ts" setup>
const emit = defineEmits<{
  apply: [];
  remove: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex items-center gap-1">
    <RuiTooltip
      :popper="{ placement: 'top' }"
      :open-delay="400"
    >
      <template #activator>
        <RuiButton
          color="primary"
          variant="text"
          size="sm"
          class="!p-2"
          icon
          @click="emit('apply')"
        >
          <RuiIcon
            size="16"
            name="lu-corner-left-up"
          />
        </RuiButton>
      </template>
      <span>
        {{ t('table_filter.saved_filters.actions.apply') }}
      </span>
    </RuiTooltip>

    <RuiTooltip
      :popper="{ placement: 'top' }"
      :open-delay="400"
    >
      <template #activator>
        <RuiButton
          color="primary"
          variant="text"
          size="sm"
          class="!p-2"
          icon
          @click="emit('remove')"
        >
          <RuiIcon
            size="16"
            name="lu-trash-2"
          />
        </RuiButton>
      </template>
      <span>
        {{ t('table_filter.saved_filters.actions.remove') }}
      </span>
    </RuiTooltip>
  </div>
</template>
