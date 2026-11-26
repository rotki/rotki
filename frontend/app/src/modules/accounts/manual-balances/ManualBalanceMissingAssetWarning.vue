<script setup lang="ts">
import type { HTMLAttributes } from 'vue';
import { RuiChip, RuiIcon, RuiTooltip } from '@rotki/ui-library';
import { useI18n } from 'vue-i18n';

defineProps<
  /* @vue-ignore */ HTMLAttributes
>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiTooltip :open-delay="200">
    <template #activator>
      <RuiChip
        color="warning"
        size="sm"
        class="**:[[class*=prepend]]:bg-rui-warning-darker my-4 cursor-pointer!"
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
