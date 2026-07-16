<script setup lang="ts">
import type { UnmatchedAssetMovement } from '@/modules/history/events/use-unmatched-asset-movements';
import MatchAssetMovementsContent from '@/modules/history/events/MatchAssetMovementsContent.vue';
import { PinnedNames } from '@/modules/session/types';
import CardTitle from '@/modules/shell/components/CardTitle.vue';
import { usePinnedPanel } from '@/modules/shell/pinned/use-pinned-panel';

const modelValue = defineModel<boolean>({ default: false });

const emit = defineEmits<{
  'find-match': [movement: UnmatchedAssetMovement];
}>();

const { t } = useI18n({ useScope: 'global' });

const { pin } = usePinnedPanel(PinnedNames.MATCH_ASSET_MOVEMENTS);

function selectMovement(movement: UnmatchedAssetMovement): void {
  emit('find-match', movement);
}

function closeDialog(): void {
  set(modelValue, false);
}

function pinSection(highlightedGroupIdentifier?: string): void {
  pin(highlightedGroupIdentifier ? { highlightedGroupIdentifier } : {});
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
