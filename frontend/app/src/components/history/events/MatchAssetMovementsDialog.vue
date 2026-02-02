<script setup lang="ts">
import type { HistoryEventEntryWithMeta } from '@/types/history/events/schemas';
import AssetMovementMatchingSettingsMenu from '@/components/history/events/AssetMovementMatchingSettingsMenu.vue';
import UnmatchedMovementsList from '@/components/history/events/UnmatchedMovementsList.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import { useAssetMovementMatchingApi } from '@/composables/api/history/events/asset-movement-matching';
import {
  type UnmatchedAssetMovement,
  useUnmatchedAssetMovements,
} from '@/composables/history/events/use-unmatched-asset-movements';
import { useConfirmStore } from '@/store/confirm';

const modelValue = defineModel<boolean>({ required: true });

const emit = defineEmits<{
  'find-match': [movement: UnmatchedAssetMovement];
  'refresh': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const {
  autoMatchLoading,
  ignoredLoading,
  ignoredMovements,
  loading,
  unmatchedMovements,
  refreshUnmatchedAssetMovements,
  triggerAssetMovementAutoMatching,
} = useUnmatchedAssetMovements();

const { matchAssetMovements, unlinkAssetMovement } = useAssetMovementMatchingApi();
const { show } = useConfirmStore();

const activeTab = ref<number>(0);
const ignoreLoading = ref<boolean>(false);
const selectedUnmatched = ref<string[]>([]);
const selectedIgnored = ref<string[]>([]);

function getEventEntry(movement: UnmatchedAssetMovement): HistoryEventEntryWithMeta {
  return Array.isArray(movement.events) ? movement.events[0] : movement.events;
}

const fiatMovements = computed<UnmatchedAssetMovement[]>(() =>
  get(unmatchedMovements).filter(movement => movement.isFiat),
);

function selectMovement(movement: UnmatchedAssetMovement): void {
  emit('find-match', movement);
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

function closeDialog(): void {
  set(modelValue, false);
}

async function ignoreSelectedMovements(groupIdentifiers: string[]): Promise<void> {
  set(ignoreLoading, true);
  try {
    const movements = get(unmatchedMovements).filter(m => groupIdentifiers.includes(m.groupIdentifier));
    for (const movement of movements) {
      const eventEntry = getEventEntry(movement);
      await matchAssetMovements(eventEntry.entry.identifier);
    }
    await refreshUnmatchedAssetMovements();
    set(selectedUnmatched, []);
  }
  finally {
    set(ignoreLoading, false);
  }
}

async function unignoreSelectedMovements(groupIdentifiers: string[]): Promise<void> {
  set(ignoreLoading, true);
  try {
    const movements = get(ignoredMovements).filter(m => groupIdentifiers.includes(m.groupIdentifier));
    for (const movement of movements) {
      const eventEntry = getEventEntry(movement);
      await unlinkAssetMovement(eventEntry.entry.identifier);
    }
    await refreshUnmatchedAssetMovements();
    set(selectedIgnored, []);
  }
  finally {
    set(ignoreLoading, false);
  }
}

function confirmIgnoreSelected(): void {
  const count = get(selectedUnmatched).length;
  show({
    message: t('asset_movement_matching.actions.ignore_selected_confirm', { count }),
    primaryAction: t('common.actions.confirm'),
    title: t('asset_movement_matching.actions.ignore_selected'),
  }, async () => ignoreSelectedMovements(get(selectedUnmatched)));
}

function confirmUnignoreSelected(): void {
  const count = get(selectedIgnored).length;
  show({
    message: t('asset_movement_matching.actions.unignore_selected_confirm', { count }),
    primaryAction: t('common.actions.confirm'),
    title: t('asset_movement_matching.actions.unignore_selected'),
  }, async () => unignoreSelectedMovements(get(selectedIgnored)));
}

async function ignoreAllFiatMovements(): Promise<void> {
  set(ignoreLoading, true);
  try {
    for (const movement of get(fiatMovements)) {
      const eventEntry = getEventEntry(movement);
      await matchAssetMovements(eventEntry.entry.identifier);
    }
    await refreshUnmatchedAssetMovements();
    set(selectedUnmatched, []);
  }
  finally {
    set(ignoreLoading, false);
  }
}

function confirmIgnoreAllFiat(): void {
  const count = get(fiatMovements).length;
  show({
    message: t('asset_movement_matching.actions.ignore_fiat_confirm', { count }),
    primaryAction: t('common.actions.confirm'),
    title: t('asset_movement_matching.actions.ignore_fiat'),
  }, async () => ignoreAllFiatMovements());
}

onBeforeMount(async () => {
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
            v-model:selected="selectedUnmatched"
            :movements="unmatchedMovements"
            :ignore-loading="ignoreLoading"
            :loading="loading"
            @ignore="ignoreMovement($event)"
            @select="selectMovement($event)"
          />
        </RuiTabItem>
        <RuiTabItem>
          <UnmatchedMovementsList
            v-model:selected="selectedIgnored"
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
              :disabled="selectedUnmatched.length === 0 || ignoreLoading"
              :loading="ignoreLoading"
              @click="confirmIgnoreSelected()"
            >
              {{ t('asset_movement_matching.actions.ignore_selected') }}
              <RuiChip
                v-if="selectedUnmatched.length > 0"
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
              class="pl-3"
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
                    class="!rounded-r-none h-9"
                    :disabled="unmatchedMovements.length === 0 || autoMatchLoading"
                    :loading="autoMatchLoading"
                    @click="triggerAssetMovementAutoMatching()"
                  >
                    {{ t('asset_movement_matching.actions.auto_match') }}
                  </RuiButton>
                </template>
                {{ t('asset_movement_matching.actions.auto_match_tooltip') }}
              </RuiTooltip>

              <AssetMovementMatchingSettingsMenu :disabled="autoMatchLoading" />
            </RuiButtonGroup>
          </div>
          <div
            v-else
            class="flex gap-2"
          >
            <RuiButton
              variant="outlined"
              color="primary"
              :disabled="selectedIgnored.length === 0 || ignoreLoading"
              :loading="ignoreLoading"
              @click="confirmUnignoreSelected()"
            >
              {{ t('asset_movement_matching.actions.unignore_selected') }}
              <RuiChip
                v-if="selectedIgnored.length > 0"
                size="sm"
                color="primary"
                class="ml-2 !py-0"
              >
                {{ selectedIgnored.length }}
              </RuiChip>
            </RuiButton>
          </div>
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
</template>
