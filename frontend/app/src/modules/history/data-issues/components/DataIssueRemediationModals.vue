<script setup lang="ts">
import type { EventPriceUpdatePayload } from '@/modules/history/events/prices/use-event-price-update-trigger';
import type { UnmatchedAssetMovement } from '@/modules/history/events/use-unmatched-asset-movements';
import type { GroupEventData, StandaloneEventData } from '@/modules/history/management/forms/form-types';
import { set } from '@vueuse/shared';
import { ref, shallowRef, watch } from 'vue';
import HistoryEventFormDialog from '@/modules/history/events/HistoryEventFormDialog.vue';
import { assetMovementMatchingKind } from '@/modules/history/events/matching/asset-movement-matching-kind';
import PotentialMatchesDialog from '@/modules/history/events/PotentialMatchesDialog.vue';
import EventAssetPriceUpdateDialog from '@/modules/history/events/prices/EventAssetPriceUpdateDialog.vue';
import UnmatchedMatchingDialog from '@/modules/history/events/UnmatchedMatchingDialog.vue';

const priceUpdate = defineModel<EventPriceUpdatePayload | undefined>('priceUpdate', { required: true });
const eventForm = defineModel<GroupEventData | StandaloneEventData | undefined>('eventForm', { required: true });
const matchingOpen = defineModel<boolean>('matchingOpen', { required: true });
const subModalOpen = defineModel<boolean>('subModalOpen', { default: false });

const emit = defineEmits<{
  saved: [];
}>();

const selectedMovement = ref<UnmatchedAssetMovement>();
const potentialMatchesOpen = shallowRef<boolean>(false);

watch(potentialMatchesOpen, (open) => {
  set(subModalOpen, open);
  if (!open)
    set(selectedMovement, undefined);
});

function openPotentialMatches(item: UnmatchedAssetMovement): void {
  set(selectedMovement, item);
  set(potentialMatchesOpen, true);
}

function onMatched(): void {
  set(potentialMatchesOpen, false);
  set(selectedMovement, undefined);
  set(matchingOpen, false);
  emit('saved');
}

function onPinned(): void {
  set(potentialMatchesOpen, false);
  set(selectedMovement, undefined);
  set(matchingOpen, false);
}
</script>

<template>
  <EventAssetPriceUpdateDialog
    v-model="priceUpdate"
    @saved="emit('saved')"
  />
  <HistoryEventFormDialog
    v-model="eventForm"
    @refresh="emit('saved')"
  />
  <UnmatchedMatchingDialog
    v-model="matchingOpen"
    :kind="assetMovementMatchingKind"
    @find-match="openPotentialMatches($event)"
  />
  <PotentialMatchesDialog
    v-if="selectedMovement"
    v-model="potentialMatchesOpen"
    :kind="assetMovementMatchingKind"
    :item="selectedMovement"
    @matched="onMatched()"
    @pinned="onPinned()"
  />
</template>
