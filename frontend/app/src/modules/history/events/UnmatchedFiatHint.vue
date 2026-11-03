<script setup lang="ts">
const { dense = false } = defineProps<{
  dense?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiTooltip
    :open-delay="400"
    :options="{ placement: 'top' }"
    :class-names="{ tooltip: 'max-w-80' }"
  >
    <template #activator>
      <RuiChip
        size="sm"
        color="warning"
        :class="{ 'py-0!': dense }"
      >
        {{ t('asset_movement_matching.fiat_hint.label') }}
      </RuiChip>
    </template>
    {{ t('asset_movement_matching.fiat_hint.tooltip') }}
  </RuiTooltip>
</template>
