<script setup lang="ts">
const visible = defineModel<boolean>({ required: true });

const { t } = useI18n({ useScope: 'global' });

function toggleVisibility(): void {
  set(visible, !get(visible));
}
</script>

<template>
  <RuiTooltip :open-delay="300">
    <template #activator>
      <RuiButton
        variant="outlined"
        color="primary"
        size="sm"
        :class="{ '!bg-rui-primary !text-white': visible }"
        data-testid="balance-divergence-toggle"
        @click="toggleVisibility()"
      >
        <RuiIcon
          name="lu-search"
          size="16"
        />
      </RuiButton>
    </template>
    {{ t('balance_divergence.action') }}
  </RuiTooltip>
</template>
