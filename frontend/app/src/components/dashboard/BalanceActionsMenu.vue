<script setup lang="ts">
import HistoricalBalancesDialog from '@/components/dashboard/HistoricalBalancesDialog.vue';
import SnapshotActionButton from '@/components/dashboard/SnapshotActionButton.vue';
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';

const { t } = useI18n({ useScope: 'global' });

const actionsMenuOpen = ref<boolean>(false);
const historicalBalancesDialogOpen = ref<boolean>(false);
const snapshotMenuOpen = ref<boolean>(false);
</script>

<template>
  <div class="flex">
    <RuiMenu
      v-model="actionsMenuOpen"
      :popper="{ placement: 'bottom-end' }"
      :persistent="historicalBalancesDialogOpen || snapshotMenuOpen"
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
          @click="historicalBalancesDialogOpen = true; actionsMenuOpen = false"
        >
          <template #prepend>
            <RuiIcon name="lu-history" />
          </template>
          {{ t('overall_balances.historical_balances') }}
        </RuiButton>
      </div>
    </RuiMenu>

    <HistoricalBalancesDialog v-model="historicalBalancesDialogOpen" />
  </div>
</template>
