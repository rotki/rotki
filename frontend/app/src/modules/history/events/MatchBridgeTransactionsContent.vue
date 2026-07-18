<script setup lang="ts">
import AssetMovementMatchingSettingsMenu from '@/modules/history/events/AssetMovementMatchingSettingsMenu.vue';
import UnmatchedBridgesList from '@/modules/history/events/UnmatchedBridgesList.vue';
import { useBridgeTransactionActions } from '@/modules/history/events/use-bridge-transaction-actions';
import { type UnmatchedBridgeTransaction, useUnmatchedBridgeTransactions } from '@/modules/history/events/use-unmatched-bridge-transactions';

const { isPinned, onActionComplete } = defineProps<{
  highlightedGroupIdentifier?: string;
  isPinned?: boolean;
  onActionComplete?: () => Promise<void>;
}>();

const emit = defineEmits<{
  'close': [];
  'pin': [];
  'select': [transaction: UnmatchedBridgeTransaction];
  'show-in-events': [transaction: UnmatchedBridgeTransaction];
}>();

const { t } = useI18n({ useScope: 'global' });

const activeTab = ref<number>(0);

const {
  autoMatchLoading,
  autoMatchMinimumTier,
  ignoredLoading,
  ignoredTransactions,
  isAutoMatchAllowed,
  loading,
  refreshUnmatchedBridgeTransactions,
  triggerBridgeAutoMatching,
  unmatchedTransactions,
} = useUnmatchedBridgeTransactions();

const {
  confirmIgnoreSelected,
  confirmMarkExternal,
  confirmRestoreSelected,
  ignoreLoading,
  ignoreTransaction,
  restoreTransaction,
  selectedIgnored,
  selectedUnmatched,
} = useBridgeTransactionActions({ onActionComplete });

const buttonSize = computed<'sm' | 'lg'>(() => isPinned ? 'sm' : 'lg');

onBeforeMount(async () => {
  await refreshUnmatchedBridgeTransactions();
});
</script>

<template>
  <RuiTabs
    v-model="activeTab"
    class="border-b border-default"
    color="primary"
  >
    <RuiTab>
      {{ t('asset_movement_matching.tabs.unmatched') }}
      <RuiChip
        v-if="unmatchedTransactions.length > 0"
        color="primary"
        size="sm"
        class="ml-2 !px-0.5 !py-0"
      >
        {{ unmatchedTransactions.length }}
      </RuiChip>
    </RuiTab>
    <RuiTab>
      {{ t('asset_movement_matching.tabs.ignored') }}
      <RuiChip
        v-if="ignoredTransactions.length > 0"
        color="secondary"
        size="sm"
        class="ml-2 !px-0.5 !py-0"
      >
        {{ ignoredTransactions.length }}
      </RuiChip>
    </RuiTab>
  </RuiTabs>

  <RuiTabItems
    v-model="activeTab"
    class="my-4"
    :class="{ 'px-3': isPinned }"
  >
    <RuiTabItem>
      <UnmatchedBridgesList
        v-model:selected="selectedUnmatched"
        :transactions="unmatchedTransactions"
        :highlighted-group-identifier="highlightedGroupIdentifier"
        :ignore-loading="ignoreLoading"
        :is-pinned="isPinned"
        :loading="loading"
        :match-disabled="!isAutoMatchAllowed"
        :match-minimum-tier="autoMatchMinimumTier"
        @ignore="ignoreTransaction($event)"
        @mark-external="confirmMarkExternal($event)"
        @pin="emit('pin')"
        @select="emit('select', $event)"
        @show-in-events="emit('show-in-events', $event)"
      />
    </RuiTabItem>
    <RuiTabItem>
      <UnmatchedBridgesList
        v-model:selected="selectedIgnored"
        :transactions="ignoredTransactions"
        :highlighted-group-identifier="highlightedGroupIdentifier"
        :loading="ignoredLoading"
        :ignore-loading="ignoreLoading"
        :is-pinned="isPinned"
        show-restore
        @pin="emit('pin')"
        @restore="restoreTransaction($event)"
        @show-in-events="emit('show-in-events', $event)"
      />
    </RuiTabItem>
  </RuiTabItems>

  <div
    class="w-full flex justify-between gap-2"
    :class="isPinned ? 'px-3 py-2 border-t border-default' : 'pb-4'"
  >
    <div
      v-if="activeTab === 0"
      class="flex"
    >
      <RuiButton
        variant="outlined"
        color="primary"
        :size="buttonSize"
        :class="{ 'h-[30px]': isPinned }"
        :disabled="selectedUnmatched.length === 0 || ignoreLoading"
        :loading="ignoreLoading"
        @click="confirmIgnoreSelected()"
      >
        {{ t('asset_movement_matching.actions.ignore_selected') }}
        <RuiChip
          v-if="!isPinned && selectedUnmatched.length > 0"
          size="sm"
          color="primary"
          class="ml-2 !py-0"
        >
          {{ selectedUnmatched.length }}
        </RuiChip>
      </RuiButton>
      <RuiButtonGroup
        color="primary"
        :class="isPinned ? '!pl-2' : 'pl-3' "
        :disabled="!isAutoMatchAllowed || autoMatchLoading"
      >
        <RuiTooltip
          :open-delay="400"
          :popper="{ placement: 'top' }"
          tooltip-class="max-w-80"
        >
          <template #activator>
            <RuiButton
              color="primary"
              class="!rounded-r-none"
              :size="buttonSize"
              :class="{ 'h-[30px] !px-3': isPinned }"
              :disabled="!isAutoMatchAllowed || unmatchedTransactions.length === 0 || autoMatchLoading"
              :loading="autoMatchLoading"
              @click="triggerBridgeAutoMatching()"
            >
              {{ t('asset_movement_matching.actions.auto_match') }}
            </RuiButton>
          </template>
          {{ t('bridge_matching.actions.auto_match_tooltip') }}
        </RuiTooltip>

        <AssetMovementMatchingSettingsMenu
          :disabled="autoMatchLoading"
          :is-pinned="isPinned"
        />
      </RuiButtonGroup>
    </div>
    <div
      v-else
      class="flex gap-2"
    >
      <RuiButton
        variant="outlined"
        color="primary"
        :size="buttonSize"
        :disabled="selectedIgnored.length === 0 || ignoreLoading"
        :loading="ignoreLoading"
        @click="confirmRestoreSelected()"
      >
        {{ t('asset_movement_matching.actions.restore_selected') }}
        <RuiChip
          v-if="!isPinned && selectedIgnored.length > 0"
          size="sm"
          color="primary"
          class="ml-2 !py-0"
        >
          {{ selectedIgnored.length }}
        </RuiChip>
      </RuiButton>
    </div>
    <RuiButton
      v-if="!isPinned"
      variant="text"
      @click="emit('close')"
    >
      {{ t('common.actions.close') }}
    </RuiButton>
  </div>
</template>
