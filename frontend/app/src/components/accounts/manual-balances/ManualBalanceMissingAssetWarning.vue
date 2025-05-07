<script setup lang="ts">
const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiTooltip :open-delay="200">
    <template #activator>
      <RuiChip
        color="warning"
        size="sm"
        class="[&_[class*=prepend]]:bg-rui-warning-darker my-4 !cursor-pointer"
      >
        <template #prepend>
          <RuiIcon
            name="lu-circle-alert"
            size="16"
          />
        </template>

        {{ t('manual_balances_table.missing_asset.title') }}
      </RuiChip>
    </template>
    {{ t('manual_balances_table.missing_asset.tooltip') }}
  </RuiTooltip>
</template>
