<script setup lang="ts">
const { disabled = false, hasOptions = false } = defineProps<{
  disabled?: boolean;
  hasOptions?: boolean;
}>();

const emit = defineEmits<{
  'redecode': [];
  'redecode-with-options': [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiButton
    variant="list"
    :class="{ '!py-2': hasOptions }"
    :disabled="disabled"
    @click="emit('redecode')"
  >
    <template #prepend>
      <RuiIcon name="lu-rotate-ccw" />
    </template>
    {{ t('transactions.actions.redecode_events') }}
    <template #append>
      <RuiTooltip
        v-if="hasOptions"
        :options="{ autoUpdate: { resize: false, scroll: false }, placement: 'top' }"
      >
        <template #activator>
          <RuiButton
            icon
            variant="text"
            size="sm"
            class="!p-2"
            :disabled="disabled"
            @click.stop="emit('redecode-with-options')"
          >
            <RuiIcon
              name="lu-settings-2"
              size="16"
            />
          </RuiButton>
        </template>
        {{ t('transactions.actions.redecode_with_options') }}
      </RuiTooltip>
    </template>
  </RuiButton>
</template>
