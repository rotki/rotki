<script setup lang="ts">
import SnapshotActionButton from '@/components/dashboard/SnapshotActionButton.vue';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import { useHistoricalBalances } from '@/composables/balances/historical';

const { t } = useI18n({ useScope: 'global' });

const actionsMenuOpen = ref<boolean>(false);
const snapshotMenuOpen = ref<boolean>(false);

const { dialogOpen, openDialog } = useHistoricalBalances();

function handleHistoricalBalancesClick(): void {
  openDialog();
  set(actionsMenuOpen, false);
}
</script>

<template>
  <RuiMenu
    v-model="actionsMenuOpen"
    :popper="{ placement: 'bottom-end' }"
    :persistent="dialogOpen || snapshotMenuOpen"
  >
    <template #activator="{ attrs }">
      <MenuTooltipButton
        :tooltip="t('overall_balances.actions_menu_tooltip')"
        size="sm"
        custom-color
        v-bind="attrs"
        class="!p-2"
      >
        <RuiIcon name="lu-ellipsis-vertical" />
      </MenuTooltipButton>
    </template>

    <div class="py-2">
      <SnapshotActionButton v-model="snapshotMenuOpen" />
      <RuiButton
        variant="list"
        @click="handleHistoricalBalancesClick()"
      >
        <template #prepend>
          <RuiIcon name="lu-history" />
        </template>
        {{ t('overall_balances.historical_balances') }}
      </RuiButton>
    </div>
  </RuiMenu>
</template>
