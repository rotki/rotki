<script setup lang="ts">
import { startPromise } from '@shared/utils';
import AssetMovementMatchingSettingsMenu from '@/modules/history/events/AssetMovementMatchingSettingsMenu.vue';
import { UNMATCHED_ACTIONS, type UnmatchedActionPayload } from '@/modules/history/events/unmatched-actions';
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
  confirmCreateCounterpart,
  confirmIgnoreSelected,
  confirmRestoreSelected,
  ignoreLoading,
  ignoreTransaction,
  markExternal,
  restoreTransaction,
  modelSelectedIgnored,
  modelSelectedUnmatched,
} = useBridgeTransactionActions({ onActionComplete });

const buttonSize = computed<'sm' | 'lg'>(() => isPinned ? 'sm' : 'lg');

function handleAction({ action, item }: UnmatchedActionPayload<UnmatchedBridgeTransaction>): void {
  switch (action) {
    case UNMATCHED_ACTIONS.CREATE_COUNTERPART:
      confirmCreateCounterpart(item);
      break;
    case UNMATCHED_ACTIONS.FIND_MATCH:
      emit('select', item);
      break;
    case UNMATCHED_ACTIONS.IGNORE:
      startPromise(ignoreTransaction(item));
      break;
    case UNMATCHED_ACTIONS.MARK_EXTERNAL:
      startPromise(markExternal(item));
      break;
    case UNMATCHED_ACTIONS.RESTORE:
      startPromise(restoreTransaction(item));
      break;
    case UNMATCHED_ACTIONS.SHOW_IN_EVENTS:
      emit('show-in-events', item);
      break;
  }
}

onBeforeMount(async () => {
  await refreshUnmatchedBridgeTransactions();
});
</script>

<template>
  <RuiTabs
    v-model="activeTab"
    class="border-b border-default shrink-0"
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

  <!-- Pinned bypasses RuiTabItems: it sizes itself from its content and hides the overflow, so
       in a bounded column the bottom of the panel - the pager - is silently cut off. Rendering
       the active list straight into a flex column lets it size to the space it actually has. -->
  <div
    v-if="isPinned"
    class="flex-1 min-h-0 flex flex-col px-3 my-4"
  >
    <UnmatchedBridgesList
      v-if="activeTab === 0"
      v-model:selected="modelSelectedUnmatched"
      :transactions="unmatchedTransactions"
      :highlighted-group-identifier="highlightedGroupIdentifier"
      :ignore-loading="ignoreLoading"
      is-pinned
      :loading="loading"
      :match-disabled="!isAutoMatchAllowed"
      :match-minimum-tier="autoMatchMinimumTier"
      @action="handleAction($event)"
      @pin="emit('pin')"
    />
    <UnmatchedBridgesList
      v-else
      v-model:selected="modelSelectedIgnored"
      :transactions="ignoredTransactions"
      :highlighted-group-identifier="highlightedGroupIdentifier"
      :loading="ignoredLoading"
      :ignore-loading="ignoreLoading"
      is-pinned
      show-restore
      @action="handleAction($event)"
      @pin="emit('pin')"
    />
  </div>

  <RuiTabItems
    v-else
    v-model="activeTab"
    class="my-4"
  >
    <RuiTabItem>
      <UnmatchedBridgesList
        v-model:selected="modelSelectedUnmatched"
        :transactions="unmatchedTransactions"
        :highlighted-group-identifier="highlightedGroupIdentifier"
        :ignore-loading="ignoreLoading"
        :loading="loading"
        :match-disabled="!isAutoMatchAllowed"
        :match-minimum-tier="autoMatchMinimumTier"
        @action="handleAction($event)"
        @pin="emit('pin')"
      />
    </RuiTabItem>
    <RuiTabItem>
      <UnmatchedBridgesList
        v-model:selected="modelSelectedIgnored"
        :transactions="ignoredTransactions"
        :highlighted-group-identifier="highlightedGroupIdentifier"
        :loading="ignoredLoading"
        :ignore-loading="ignoreLoading"
        show-restore
        @action="handleAction($event)"
        @pin="emit('pin')"
      />
    </RuiTabItem>
  </RuiTabItems>

  <div
    class="w-full flex justify-between gap-2"
    :class="isPinned ? 'px-3 py-2 border-t border-default' : 'pb-4'"
  >
    <div
      v-if="activeTab === 0"
      class="flex grow"
    >
      <RuiButton
        v-if="modelSelectedUnmatched.length > 0"
        variant="outlined"
        color="primary"
        :size="buttonSize"
        :class="{ 'h-[30px]': isPinned }"
        :disabled="ignoreLoading"
        :loading="ignoreLoading"
        @click="confirmIgnoreSelected()"
      >
        {{ t('asset_movement_matching.actions.ignore_selected') }}
        <RuiChip
          v-if="!isPinned && modelSelectedUnmatched.length > 0"
          size="sm"
          color="primary"
          class="ml-2 !py-0"
        >
          {{ modelSelectedUnmatched.length }}
        </RuiChip>
      </RuiButton>
      <RuiButtonGroup
        color="primary"
        class="grow justify-end"
        :class="isPinned && modelSelectedUnmatched.length > 0 ? '!pl-2' : ''"
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
        v-if="modelSelectedIgnored.length > 0"
        variant="outlined"
        color="primary"
        :size="buttonSize"
        :disabled="ignoreLoading"
        :loading="ignoreLoading"
        @click="confirmRestoreSelected()"
      >
        {{ t('asset_movement_matching.actions.restore_selected') }}
        <RuiChip
          v-if="!isPinned && modelSelectedIgnored.length > 0"
          size="sm"
          color="primary"
          class="ml-2 !py-0"
        >
          {{ modelSelectedIgnored.length }}
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
