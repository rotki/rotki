<script setup lang="ts">
import type { Nullable } from '@rotki/common';
import type { UnmatchedAssetMovement } from '@/modules/history/events/use-unmatched-asset-movements';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import MatchAssetMovementsContent from '@/modules/history/events/MatchAssetMovementsContent.vue';
import { type Pinned, PinnedNames } from '@/modules/session/types';
import CardTitle from '@/modules/shell/components/CardTitle.vue';

const modelValue = defineModel<boolean>({ default: false });

const emit = defineEmits<{
  'find-match': [movement: UnmatchedAssetMovement];
}>();

const { t } = useI18n({ useScope: 'global' });

const { pinned, showPinned } = storeToRefs(useAreaVisibilityStore());

function selectMovement(movement: UnmatchedAssetMovement): void {
  emit('find-match', movement);
}

function closeDialog(): void {
  set(modelValue, false);
}

function setPinned(pin: Nullable<Pinned>): void {
  set(pinned, pin);
}

function pinSection(highlightedGroupIdentifier?: string): void {
  const pin: Pinned = {
    name: PinnedNames.MATCH_ASSET_MOVEMENTS,
    props: highlightedGroupIdentifier ? { highlightedGroupIdentifier } : {},
  };

  setPinned(pin);
  set(showPinned, true);
  set(modelValue, false);
}

function showInHistoryEvents(movement: UnmatchedAssetMovement): void {
  pinSection(movement.groupIdentifier);
}
</script>

<template>
  <RuiDialog
    v-model="modelValue"
    max-width="1000"
  >
    <RuiCard
      content-class="!py-0"
      divide
    >
      <template #custom-header>
        <div class="flex items-center justify-between w-full px-4 py-2">
          <CardTitle>
            {{ t('asset_movement_matching.dialog.title') }}
          </CardTitle>
          <RuiButton
            variant="text"
            icon
            @click="closeDialog()"
          >
            <RuiIcon name="lu-x" />
          </RuiButton>
        </div>
      </template>

      <MatchAssetMovementsContent
        @close="closeDialog()"
        @pin="pinSection()"
        @select="selectMovement($event)"
        @show-in-events="showInHistoryEvents($event)"
      />
    </RuiCard>
  </RuiDialog>
</template>
