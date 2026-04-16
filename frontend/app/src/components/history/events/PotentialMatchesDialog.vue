<script setup lang="ts">
import type { UnmatchedAssetMovement } from '@/composables/history/events/use-unmatched-asset-movements';
import PotentialMatchesContent from '@/components/history/events/PotentialMatchesContent.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import { useAreaVisibilityStore } from '@/modules/common/use-area-visibility-store';
import { type Pinned, PinnedNames } from '@/modules/session/types';

const modelValue = defineModel<boolean>({ required: true });

const { movement } = defineProps<{
  movement: UnmatchedAssetMovement;
}>();

const emit = defineEmits<{
  matched: [];
  pinned: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const { pinned, showPinned } = storeToRefs(useAreaVisibilityStore());

function closeDialog(): void {
  set(modelValue, false);
}

function onMatched(): void {
  set(modelValue, false);
  emit('matched');
}

function showUnmatchedInEvents(): void {
  const pin: Pinned = {
    name: PinnedNames.MATCH_ASSET_MOVEMENTS,
    props: { highlightedGroupIdentifier: movement.groupIdentifier },
  };

  set(pinned, pin);
  set(showPinned, true);
  set(modelValue, false);
  emit('pinned');
}

function showPotentialMatchInEvents(data: { identifier: number; groupIdentifier: string }): void {
  const pin: Pinned = {
    name: PinnedNames.MATCH_ASSET_MOVEMENTS,
    props: {
      highlightedGroupIdentifier: movement.groupIdentifier,
      highlightedPotentialMatchIdentifier: data.identifier,
      potentialMatchGroupIdentifier: data.groupIdentifier,
    },
  };

  set(pinned, pin);
  set(showPinned, true);
  set(modelValue, false);
  emit('pinned');
}
</script>

<template>
  <RuiDialog
    v-model="modelValue"
    max-width="1000"
  >
    <RuiCard content-class="!pb-0">
      <template #custom-header>
        <div class="flex items-center justify-between w-full px-4 pt-2">
          <CardTitle>
            {{ t('asset_movement_matching.dialog.select_match_title') }}
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

      <PotentialMatchesContent
        :movement="movement"
        @close="closeDialog()"
        @matched="onMatched()"
        @show-in-events="showPotentialMatchInEvents($event)"
        @show-unmatched-in-events="showUnmatchedInEvents()"
      />
    </RuiCard>
  </RuiDialog>
</template>
