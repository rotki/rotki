<script setup lang="ts">
import PotentialMatchesDialog from '@/components/history/events/PotentialMatchesDialog.vue';
import UnmatchedMovementsList from '@/components/history/events/UnmatchedMovementsList.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import {
  type UnmatchedAssetMovement,
  useUnmatchedAssetMovements,
} from '@/composables/history/events/use-unmatched-asset-movements';

const modelValue = defineModel<boolean>({ required: true });

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const {
  fetchUnmatchedAssetMovements,
  loading,
  unmatchedMovements,
} = useUnmatchedAssetMovements();

const selectedMovement = ref<UnmatchedAssetMovement>();
const showPotentialMatchesDialog = ref<boolean>(false);

function selectMovement(movement: UnmatchedAssetMovement): void {
  set(selectedMovement, movement);
  set(showPotentialMatchesDialog, true);
}

function onMatched(): void {
  set(selectedMovement, undefined);
  emit('refresh');
}

function closeDialog(): void {
  set(modelValue, false);
}

onMounted(async () => {
  await fetchUnmatchedAssetMovements();
});
</script>

<template>
  <RuiDialog
    v-model="modelValue"
    max-width="900"
  >
    <RuiCard content-class="!py-0 max-h-[calc(100vh-250px)]">
      <template #custom-header>
        <div class="flex items-center justify-between w-full px-4 pt-2">
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

      <div
        v-if="loading"
        class="flex items-center justify-center p-8"
      >
        <RuiProgress
          circular
          variant="indeterminate"
        />
      </div>

      <UnmatchedMovementsList
        v-else
        :movements="unmatchedMovements"
        @select="selectMovement($event)"
      />

      <template #footer>
        <div class="w-full flex justify-end gap-2">
          <RuiButton
            variant="text"
            @click="closeDialog()"
          >
            {{ t('common.actions.close') }}
          </RuiButton>
        </div>
      </template>
    </RuiCard>
  </RuiDialog>

  <PotentialMatchesDialog
    v-if="selectedMovement"
    v-model="showPotentialMatchesDialog"
    :movement="selectedMovement"
    @matched="onMatched()"
  />
</template>
