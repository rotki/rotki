<script setup lang="ts">
import { startPromise } from '@shared/utils';
import AssetMovementMatchingSettingsMenu from '@/modules/history/events/AssetMovementMatchingSettingsMenu.vue';
import { UNMATCHED_ACTIONS, type UnmatchedActionPayload, type UnmatchedMatchAccess } from '@/modules/history/events/unmatched-actions';
import UnmatchedBridgesList from '@/modules/history/events/UnmatchedBridgesList.vue';
import UnmatchedResolutionStrip from '@/modules/history/events/UnmatchedResolutionStrip.vue';
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
  ignoredError,
  ignoredLoading,
  ignoredTransactions,
  isAutoMatchAllowed,
  loading,
  refreshUnmatchedBridgeTransactions,
  triggerBridgeAutoMatching,
  unmatchedError,
  unmatchedTransactions,
} = useUnmatchedBridgeTransactions();

const matchAccess = computed<UnmatchedMatchAccess>(() => ({ allowed: get(isAutoMatchAllowed), minimumTier: get(autoMatchMinimumTier) }));

const {
  confirmCreateCounterpart,
  confirmIgnoreSelected,
  confirmRestoreSelected,
  dismissResolution,
  ignoreLoading,
  ignoreTransaction,
  markExternal,
  restoreTransaction,
  resolutionNotice,
  modelSelectedIgnored,
  modelSelectedUnmatched,
  undoResolution,
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
        class="ml-2 px-0.5! py-0!"
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
        class="ml-2 px-0.5! py-0!"
      >
        {{ ignoredTransactions.length }}
      </RuiChip>
    </RuiTab>
  </RuiTabs>

  <UnmatchedResolutionStrip
    v-if="resolutionNotice"
    :message="resolutionNotice.message"
    :loading="ignoreLoading"
    class="shrink-0"
    :class="isPinned ? 'mx-3 mt-3' : 'mt-4'"
    @undo="startPromise(undoResolution())"
    @dismiss="dismissResolution()"
  />

  <div
    v-if="isPinned"
    class="flex-1 min-h-0 flex flex-col px-3 my-4"
  >
    <UnmatchedBridgesList
      v-if="activeTab === 0"
      v-model:selected="modelSelectedUnmatched"
      :transactions="unmatchedTransactions"
      :error="unmatchedError"
      :highlighted-group-identifier="highlightedGroupIdentifier"
      :ignore-loading="ignoreLoading"
      is-pinned
      :loading="loading"
      :match-access="matchAccess"
      @action="handleAction($event)"
      @pin="emit('pin')"
      @retry="refreshUnmatchedBridgeTransactions()"
    />
    <UnmatchedBridgesList
      v-else
      v-model:selected="modelSelectedIgnored"
      :transactions="ignoredTransactions"
      :error="ignoredError"
      :highlighted-group-identifier="highlightedGroupIdentifier"
      :loading="ignoredLoading"
      :ignore-loading="ignoreLoading"
      is-pinned
      :match-access="matchAccess"
      show-restore
      @action="handleAction($event)"
      @pin="emit('pin')"
      @retry="refreshUnmatchedBridgeTransactions()"
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
        :error="unmatchedError"
        :highlighted-group-identifier="highlightedGroupIdentifier"
        :ignore-loading="ignoreLoading"
        :loading="loading"
        :match-access="matchAccess"
        @action="handleAction($event)"
        @pin="emit('pin')"
        @retry="refreshUnmatchedBridgeTransactions()"
      />
    </RuiTabItem>
    <RuiTabItem>
      <UnmatchedBridgesList
        v-model:selected="modelSelectedIgnored"
        :transactions="ignoredTransactions"
        :error="ignoredError"
        :highlighted-group-identifier="highlightedGroupIdentifier"
        :loading="ignoredLoading"
        :ignore-loading="ignoreLoading"
        :match-access="matchAccess"
        show-restore
        @action="handleAction($event)"
        @pin="emit('pin')"
        @retry="refreshUnmatchedBridgeTransactions()"
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
        :class="{ 'h-7.5': isPinned }"
        :disabled="ignoreLoading"
        :loading="ignoreLoading"
        data-testid="ignore-selected"
        @click="confirmIgnoreSelected()"
      >
        {{ t('asset_movement_matching.actions.ignore_selected') }}
        <RuiChip
          v-if="!isPinned && modelSelectedUnmatched.length > 0"
          size="sm"
          color="primary"
          class="ml-2 py-0!"
        >
          {{ modelSelectedUnmatched.length }}
        </RuiChip>
      </RuiButton>
      <RuiButtonGroup
        color="primary"
        class="grow justify-end"
        :class="isPinned && modelSelectedUnmatched.length > 0 ? 'pl-2!' : ''"
        :disabled="!isAutoMatchAllowed || autoMatchLoading"
      >
        <RuiTooltip
          :open-delay="400"
          :options="{ placement: 'top' }"
          :class-names="{ tooltip: 'max-w-80' }"
        >
          <template #activator>
            <RuiButton
              color="primary"
              :size="buttonSize"
              :class="{ 'h-7.5 px-3!': isPinned }"
              :disabled="!isAutoMatchAllowed || unmatchedTransactions.length === 0 || autoMatchLoading"
              :loading="autoMatchLoading"
              data-testid="auto-match"
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
        data-testid="restore-selected"
        @click="confirmRestoreSelected()"
      >
        {{ t('asset_movement_matching.actions.restore_selected') }}
        <RuiChip
          v-if="!isPinned && modelSelectedIgnored.length > 0"
          size="sm"
          color="primary"
          class="ml-2 py-0!"
        >
          {{ modelSelectedIgnored.length }}
        </RuiChip>
      </RuiButton>
    </div>
    <RuiButton
      v-if="!isPinned"
      variant="text"
      data-testid="close"
      @click="emit('close')"
    >
      {{ t('common.actions.close') }}
    </RuiButton>
  </div>
</template>
