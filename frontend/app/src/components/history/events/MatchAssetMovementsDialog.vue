<script setup lang="ts">
import type { HistoryEventEntryWithMeta } from '@/types/history/events/schemas';
import PotentialMatchesDialog from '@/components/history/events/PotentialMatchesDialog.vue';
import UnmatchedMovementsList from '@/components/history/events/UnmatchedMovementsList.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import {
  type UnmatchedAssetMovement,
  useUnmatchedAssetMovements,
} from '@/composables/history/events/use-unmatched-asset-movements';
import { useConfirmStore } from '@/store/confirm';

const modelValue = defineModel<boolean>({ required: true });

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const {
  autoMatchLoading,
  ignoredLoading,
  ignoredMovements,
  loading,
  unmatchedMovements,
  refreshUnmatchedAssetMovements,
  triggerAutoMatch,
} = useUnmatchedAssetMovements();

const { matchAssetMovements, unlinkAssetMovement } = useHistoryEventsApi();
const { show } = useConfirmStore();

const activeTab = ref<number>(0);
const selectedMovement = ref<UnmatchedAssetMovement>();
const showPotentialMatchesDialog = ref<boolean>(false);
const ignoreLoading = ref<boolean>(false);

function getEventEntry(movement: UnmatchedAssetMovement): HistoryEventEntryWithMeta {
  const events = Array.isArray(movement.events) ? movement.events : [movement.events];
  return events[0];
}

const fiatMovements = computed<UnmatchedAssetMovement[]>(() =>
  get(unmatchedMovements).filter(movement => movement.isFiat),
);

function selectMovement(movement: UnmatchedAssetMovement): void {
  set(selectedMovement, movement);
  set(showPotentialMatchesDialog, true);
}

async function ignoreMovement(movement: UnmatchedAssetMovement): Promise<void> {
  set(ignoreLoading, true);
  try {
    const eventEntry = getEventEntry(movement);
    await matchAssetMovements(eventEntry.entry.identifier);
    await refreshUnmatchedAssetMovements();
  }
  finally {
    set(ignoreLoading, false);
  }
}

async function restoreMovement(movement: UnmatchedAssetMovement): Promise<void> {
  set(ignoreLoading, true);
  try {
    const eventEntry = getEventEntry(movement);
    await unlinkAssetMovement(eventEntry.entry.identifier);
    await refreshUnmatchedAssetMovements();
  }
  finally {
    set(ignoreLoading, false);
  }
}

function onMatched(): void {
  set(selectedMovement, undefined);
  emit('refresh');
}

function closeDialog(): void {
  set(modelValue, false);
}

async function ignoreAllMovements(movements: UnmatchedAssetMovement[]): Promise<void> {
  set(ignoreLoading, true);
  try {
    for (const movement of movements) {
      const eventEntry = getEventEntry(movement);
      await matchAssetMovements(eventEntry.entry.identifier);
    }
    await refreshUnmatchedAssetMovements();
  }
  finally {
    set(ignoreLoading, false);
  }
}

function confirmIgnoreAll(): void {
  const count = get(unmatchedMovements).length;
  show({
    message: t('asset_movement_matching.actions.ignore_all_confirm', { count }),
    primaryAction: t('common.actions.confirm'),
    title: t('asset_movement_matching.actions.ignore_all'),
  }, async () => ignoreAllMovements(get(unmatchedMovements)));
}

function confirmIgnoreAllFiat(): void {
  const count = get(fiatMovements).length;
  show({
    message: t('asset_movement_matching.actions.ignore_fiat_confirm', { count }),
    primaryAction: t('common.actions.confirm'),
    title: t('asset_movement_matching.actions.ignore_fiat'),
  }, async () => ignoreAllMovements(get(fiatMovements)));
}

onMounted(async () => {
  await refreshUnmatchedAssetMovements();
});
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
      >
        <RuiTabItem>
          <UnmatchedMovementsList
            :movements="unmatchedMovements"
            :ignore-loading="ignoreLoading"
            :loading="loading"
            @ignore="ignoreMovement($event)"
            @select="selectMovement($event)"
          />
        </RuiTabItem>
        <RuiTabItem>
          <UnmatchedMovementsList
            :movements="ignoredMovements"
            :loading="ignoredLoading"
            :ignore-loading="ignoreLoading"
            show-restore
            @restore="restoreMovement($event)"
          />
        </RuiTabItem>
      </RuiTabItems>

      <template #footer>
        <div class="w-full flex justify-between gap-2 pt-2">
          <div
            v-if="activeTab === 0"
            class="flex gap-2"
          >
            <RuiButton
              variant="outlined"
              color="primary"
              :disabled="unmatchedMovements.length === 0 || ignoreLoading"
              :loading="ignoreLoading"
              @click="confirmIgnoreAll()"
            >
              {{ t('asset_movement_matching.actions.ignore_all') }}
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
                  :disabled="fiatMovements.length === 0 || ignoreLoading"
                  :loading="ignoreLoading"
                  @click="confirmIgnoreAllFiat()"
                >
                  {{ t('asset_movement_matching.actions.ignore_fiat') }}
                </RuiButton>
              </template>
              {{ t('asset_movement_matching.actions.ignore_fiat_tooltip') }}
            </RuiTooltip>
            <RuiTooltip
              :open-delay="400"
              :popper="{ placement: 'top' }"
              tooltip-class="max-w-80"
              class="border-l border-default pl-2"
            >
              <template #activator>
                <RuiButton
                  color="primary"
                  :disabled="unmatchedMovements.length === 0 || autoMatchLoading"
                  :loading="autoMatchLoading"
                  @click="triggerAutoMatch()"
                >
                  {{ t('asset_movement_matching.actions.auto_match') }}
                </RuiButton>
              </template>
              {{ t('asset_movement_matching.actions.auto_match_tooltip') }}
            </RuiTooltip>
          </div>
          <div v-else />
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
