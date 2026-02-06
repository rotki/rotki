<script setup lang="ts">
import AssetMovementMatchingSettingsMenu from '@/components/history/events/AssetMovementMatchingSettingsMenu.vue';
import UnmatchedMovementsList from '@/components/history/events/UnmatchedMovementsList.vue';
import { useAssetMovementActions } from '@/composables/history/events/use-asset-movement-actions';
import { type UnmatchedAssetMovement, useUnmatchedAssetMovements } from '@/composables/history/events/use-unmatched-asset-movements';

const props = defineProps<{
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
  selectedIgnored,
  selectedUnmatched,
} = useAssetMovementActions({ onActionComplete: props.onActionComplete });

const buttonSize = computed<'sm' | undefined>(() => props.isPinned ? 'sm' : undefined);

onBeforeMount(async () => {
  await refreshUnmatchedAssetMovements();
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

  <RuiTabItems
    v-model="activeTab"
    class="my-4"
    :class="isPinned ? 'px-4' : 'px-2'"
  >
    <RuiTabItem>
      <UnmatchedMovementsList
        v-model:selected="selectedUnmatched"
        :movements="unmatchedMovements"
        :highlighted-group-identifier="highlightedGroupIdentifier"
        :ignore-loading="ignoreLoading"
        :is-pinned="isPinned"
        :loading="loading"
        @ignore="ignoreMovement($event)"
        @pin="emit('pin')"
        @select="emit('select', $event)"
        @show-in-events="emit('show-in-events', $event)"
      />
    </RuiTabItem>
    <RuiTabItem>
      <UnmatchedMovementsList
        v-model:selected="selectedIgnored"
        :movements="ignoredMovements"
        :highlighted-group-identifier="highlightedGroupIdentifier"
        :loading="ignoredLoading"
        :ignore-loading="ignoreLoading"
        :is-pinned="isPinned"
        show-restore
        @pin="emit('pin')"
        @restore="restoreMovement($event)"
        @show-in-events="emit('show-in-events', $event)"
      />
    </RuiTabItem>
  </RuiTabItems>

  <div
    class="w-full flex justify-between gap-2"
    :class="isPinned ? 'p-2 border-t border-default' : 'pb-4'"
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
            :disabled="fiatMovements.length === 0 || ignoreLoading"
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
        :disabled="autoMatchLoading"
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
              :class="isPinned ? 'h-[30px] !px-3' : 'h-9'"
              :disabled="unmatchedMovements.length === 0 || autoMatchLoading"
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
