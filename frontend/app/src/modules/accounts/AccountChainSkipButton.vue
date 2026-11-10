<script setup lang="ts">
defineProps<{
  chain: string;
  /** What a click would do, or why nothing can be done. */
  label: string;
  skipped: boolean;
  /** The chain is switched off whole in Settings, which no row action changes. */
  locked: boolean;
  pending: boolean;
}>();

const emit = defineEmits<{
  toggle: [];
}>();
</script>

<template>
  <RuiTooltip
    :open-delay="300"
    :close-delay="0"
    :class-names="{ tooltip: 'max-w-80' }"
  >
    <template #activator>
      <RuiButton
        variant="text"
        icon
        size="sm"
        :color="skipped ? 'error' : undefined"
        :disabled="locked"
        :aria-busy="pending || undefined"
        :aria-label="label"
        data-testid="account-chain-skip"
        :data-chain="chain"
        @click="emit('toggle')"
      >
        <RuiIcon
          size="16"
          :name="skipped ? 'lu-circle-check' : 'lu-ban'"
        />
      </RuiButton>
    </template>
    {{ label }}
  </RuiTooltip>
</template>
