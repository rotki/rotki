<script setup lang="ts">
import { startPromise } from '@shared/utils';
import AssetMovementMatchingSettingsMenu from '@/modules/history/events/AssetMovementMatchingSettingsMenu.vue';
import { UNMATCHED_ACTIONS, type UnmatchedActionPayload } from '@/modules/history/events/unmatched-actions';
import UnmatchedMovementsList from '@/modules/history/events/UnmatchedMovementsList.vue';
import { useAssetMovementActions } from '@/modules/history/events/use-asset-movement-actions';
import { type UnmatchedAssetMovement, useUnmatchedAssetMovements } from '@/modules/history/events/use-unmatched-asset-movements';

const { isPinned, onActionComplete } = defineProps<{
  highlightedGroupIdentifier?: string;
  isPinned?: boolean;
  onActionComplete?: () => Promise<void>;
}>();

const emit = defineEmits<{
  'close': [];
  'pin': [];
  'select': [movement: UnmatchedAssetMovement];
  'show-in-events': [movement: UnmatchedAssetMovement];
}>();

const { t } = useI18n({ useScope: 'global' });

const activeTab = ref<number>(0);

const {
  autoMatchLoading,
  autoMatchMinimumTier,
  isAutoMatchAllowed,
  ignoredLoading,
  ignoredMovements,
  loading,
  unmatchedMovements,
  refreshUnmatchedAssetMovements,
  triggerAssetMovementAutoMatching,
} = useUnmatchedAssetMovements();

const {
  confirmIgnoreAllFiat,
  confirmIgnoreSelected,
  confirmRestoreSelected,
  fiatMovements,
  ignoreLoading,
  ignoreMovement,
  restoreMovement,
  modelSelectedIgnored,
  modelSelectedUnmatched,
} = useAssetMovementActions({ onActionComplete });

const buttonSize = computed<'sm' | 'lg'>(() => isPinned ? 'sm' : 'lg');

function handleAction({ action, item }: UnmatchedActionPayload<UnmatchedAssetMovement>): void {
  switch (action) {
    case UNMATCHED_ACTIONS.FIND_MATCH:
      emit('select', item);
      break;
    case UNMATCHED_ACTIONS.IGNORE:
      startPromise(ignoreMovement(item));
      break;
    case UNMATCHED_ACTIONS.RESTORE:
      startPromise(restoreMovement(item));
      break;
    case UNMATCHED_ACTIONS.SHOW_IN_EVENTS:
      emit('show-in-events', item);
      break;
    // movements have no counterpart to create or mark external
    case UNMATCHED_ACTIONS.CREATE_COUNTERPART:
    case UNMATCHED_ACTIONS.MARK_EXTERNAL:
      break;
  }
}

onBeforeMount(async () => {
  await refreshUnmatchedAssetMovements();
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
        v-if="unmatchedMovements.length > 0"
        color="primary"
        size="sm"
        class="ml-2 !px-0.5 !py-0"
      >
        {{ unmatchedMovements.length }}
      </RuiChip>
    </RuiTab>
    <RuiTab>
      {{ t('asset_movement_matching.tabs.ignored') }}
      <RuiChip
        v-if="ignoredMovements.length > 0"
        color="secondary"
        size="sm"
        class="ml-2 !px-0.5 !py-0"
      >
        {{ ignoredMovements.length }}
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
    <UnmatchedMovementsList
      v-if="activeTab === 0"
      v-model:selected="modelSelectedUnmatched"
      :movements="unmatchedMovements"
      :highlighted-group-identifier="highlightedGroupIdentifier"
      :ignore-loading="ignoreLoading"
      is-pinned
      :loading="loading"
      :match-disabled="!isAutoMatchAllowed"
      :match-minimum-tier="autoMatchMinimumTier"
      @action="handleAction($event)"
      @pin="emit('pin')"
    />
    <UnmatchedMovementsList
      v-else
      v-model:selected="modelSelectedIgnored"
      :movements="ignoredMovements"
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
      <UnmatchedMovementsList
        v-model:selected="modelSelectedUnmatched"
        :movements="unmatchedMovements"
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
      <UnmatchedMovementsList
        v-model:selected="modelSelectedIgnored"
        :movements="ignoredMovements"
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
      class="flex"
    >
      <RuiButton
        variant="outlined"
        color="primary"
        :size="buttonSize"
        class="rounded-r-none"
        :class="{ 'h-[30px]': isPinned }"
        :disabled="!isAutoMatchAllowed || modelSelectedUnmatched.length === 0 || ignoreLoading"
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
      <RuiTooltip
        :open-delay="400"
        :popper="{ placement: 'top' }"
        tooltip-class="max-w-80"
      >
        <template #activator>
          <RuiButton
            variant="outlined"
            color="warning"
            :size="buttonSize"
            class="rounded-l-none -ml-[1px]"
            :class="{ 'h-[30px]': isPinned }"
            :disabled="!isAutoMatchAllowed || fiatMovements.length === 0 || ignoreLoading"
            :loading="ignoreLoading"
            @click="confirmIgnoreAllFiat()"
          >
            {{ t('asset_movement_matching.actions.ignore_fiat') }}
          </RuiButton>
        </template>
        {{ t('asset_movement_matching.actions.ignore_fiat_tooltip') }}
      </RuiTooltip>
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
              :disabled="!isAutoMatchAllowed || unmatchedMovements.length === 0 || autoMatchLoading"
              :loading="autoMatchLoading"
              @click="triggerAssetMovementAutoMatching()"
            >
              {{ t('asset_movement_matching.actions.auto_match') }}
            </RuiButton>
          </template>
          {{ t('asset_movement_matching.actions.auto_match_tooltip') }}
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
        :disabled="!isAutoMatchAllowed || modelSelectedIgnored.length === 0 || ignoreLoading"
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
