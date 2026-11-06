<script setup lang="ts" generic="TItem extends UnmatchedEventGroup, TRow extends UnmatchedRow<TItem>">
import type { MatchingKind } from '@/modules/history/events/matching/matching-kind';
import type { UnmatchedEventGroup } from '@/modules/history/events/matching/types';
import type { HistoryEventQuestion } from '@/modules/history/events/types';
import type { UnmatchedRow } from '@/modules/history/events/unmatched-row';
import { startPromise } from '@shared/utils';
import AssetMovementMatchingSettingsMenu from '@/modules/history/events/AssetMovementMatchingSettingsMenu.vue';
import { UNMATCHED_ACTIONS, type UnmatchedActionPayload } from '@/modules/history/events/unmatched-actions';
import UnmatchedList from '@/modules/history/events/UnmatchedList.vue';
import UnmatchedResolutionStrip from '@/modules/history/events/UnmatchedResolutionStrip.vue';
import ConfirmPopover from '@/modules/shell/components/ConfirmPopover.vue';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';

const { highlightedGroupIdentifier, isPinned, kind, onActionComplete } = defineProps<{
  kind: MatchingKind<TItem, TRow>;
  highlightedGroupIdentifier?: string;
  isPinned?: boolean;
  onActionComplete?: () => Promise<void>;
}>();

const emit = defineEmits<{
  'close': [];
  'pin': [];
  'select': [item: TItem];
  'show-in-events': [item: TItem];
}>();

const { t } = useI18n({ useScope: 'global' });

const activeTab = ref<number>(0);

const {
  autoMatch,
  autoMatchLoading,
  ignored,
  ignoredError,
  ignoredLoading,
  isAutoMatchAllowed,
  loading,
  refresh,
  unmatched,
  unmatchedError,
} = kind.useSource();

const {
  actionFailure,
  createCounterpart,
  dismissResolution,
  fiat,
  ignore,
  ignoreLoading,
  ignoreSelected,
  ignoreSelectedQuestion,
  markExternal,
  modelSelectedIgnored,
  modelSelectedUnmatched,
  resolutionNotice,
  restore,
  restoreSelected,
  undoResolution,
} = kind.useActions({ onActionComplete });

const buttonSize = computed<'sm' | 'lg'>(() => isPinned ? 'sm' : 'lg');

const bulkGated = computed<boolean>(() => kind.bulkSelection.needsTier && !get(isAutoMatchAllowed));

const showIgnoreSelected = computed<boolean>(() => !kind.bulkSelection.hideWhenEmpty || get(modelSelectedUnmatched).length > 0);

const showRestoreSelected = computed<boolean>(() => !kind.bulkSelection.hideWhenEmpty || get(modelSelectedIgnored).length > 0);

const fiatCount = computed<number>(() => (fiat ? get(fiat.items).length : 0));

const fiatQuestion = computed<HistoryEventQuestion | undefined>(() => (fiat ? get(fiat.question) : undefined));

async function ignoreAllFiat(): Promise<void> {
  await fiat?.ignoreAll();
}

const autoMatchGroupClass = computed<string>(() => {
  if (fiat)
    return isPinned ? 'pl-2!' : 'pl-3';
  return isPinned && get(modelSelectedUnmatched).length > 0 ? 'grow justify-end pl-2!' : 'grow justify-end';
});

function handleAction({ action, item }: UnmatchedActionPayload<TItem>): void {
  switch (action) {
    case UNMATCHED_ACTIONS.CREATE_COUNTERPART:
      if (createCounterpart)
        startPromise(createCounterpart(item));
      break;
    case UNMATCHED_ACTIONS.FIND_MATCH:
      emit('select', item);
      break;
    case UNMATCHED_ACTIONS.IGNORE:
      startPromise(ignore(item));
      break;
    case UNMATCHED_ACTIONS.MARK_EXTERNAL:
      startPromise(markExternal(item));
      break;
    case UNMATCHED_ACTIONS.RESTORE:
      startPromise(restore(item));
      break;
    case UNMATCHED_ACTIONS.SHOW_IN_EVENTS:
      emit('show-in-events', item);
      break;
  }
}

/** Everything a tab's list is given; the unmatched and ignored tabs differ only in their items and fetch state. */
interface ListBindings {
  kind: MatchingKind<TItem, TRow>;
  items: TItem[];
  error: unknown;
  loading: boolean;
  showRestore: boolean;
  highlightedGroupIdentifier?: string;
  ignoreLoading: boolean;
  isPinned: boolean;
}

function listBindings(showRestore: boolean): ListBindings {
  return {
    error: get(showRestore ? ignoredError : unmatchedError),
    highlightedGroupIdentifier,
    ignoreLoading: get(ignoreLoading),
    isPinned,
    items: get(showRestore ? ignored : unmatched),
    kind,
    loading: get(showRestore ? ignoredLoading : loading),
    showRestore,
  };
}

const listListeners = {
  action: handleAction,
  pin: (): void => emit('pin'),
  retry: refresh,
};

onBeforeMount(async () => {
  await refresh();
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
        v-if="unmatched.length > 0"
        color="primary"
        size="sm"
        class="ml-2 px-0.5! py-0!"
      >
        {{ unmatched.length }}
      </RuiChip>
    </RuiTab>
    <RuiTab>
      {{ t('asset_movement_matching.tabs.ignored') }}
      <RuiChip
        v-if="ignored.length > 0"
        color="secondary"
        size="sm"
        class="ml-2 px-0.5! py-0!"
      >
        {{ ignored.length }}
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

  <FailureStrip
    v-if="actionFailure"
    :retryable="false"
    :title="t(kind.messages.actionFailed)"
    :failure="actionFailure"
    class="shrink-0"
    :class="isPinned ? 'mx-3 mt-3' : 'mt-4'"
    data-testid="unmatched-action-error"
  />

  <div
    v-if="isPinned"
    class="flex-1 min-h-0 flex flex-col px-3 my-4"
  >
    <UnmatchedList
      v-if="activeTab === 0"
      v-model:selected="modelSelectedUnmatched"
      v-bind="listBindings(false)"
      v-on="listListeners"
    />
    <UnmatchedList
      v-else
      v-model:selected="modelSelectedIgnored"
      v-bind="listBindings(true)"
      v-on="listListeners"
    />
  </div>

  <RuiTabItems
    v-else
    v-model="activeTab"
    class="my-4"
  >
    <RuiTabItem>
      <UnmatchedList
        v-model:selected="modelSelectedUnmatched"
        v-bind="listBindings(false)"
        v-on="listListeners"
      />
    </RuiTabItem>
    <RuiTabItem>
      <UnmatchedList
        v-model:selected="modelSelectedIgnored"
        v-bind="listBindings(true)"
        v-on="listListeners"
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
      :class="{ grow: !fiat }"
    >
      <ConfirmPopover
        v-if="showIgnoreSelected"
        tone="warning"
        :title="ignoreSelectedQuestion.title"
        :message="ignoreSelectedQuestion.message"
        :confirm-label="t('asset_movement_matching.dialog.ignore')"
        @confirm="startPromise(ignoreSelected())"
      >
        <template #activator="{ attrs }">
          <RuiButton
            variant="outlined"
            color="primary"
            :size="buttonSize"
            :class="{ 'h-7.5': isPinned, 'rounded-r-none': fiat }"
            :disabled="bulkGated || modelSelectedUnmatched.length === 0 || ignoreLoading"
            :loading="ignoreLoading"
            data-testid="ignore-selected"
            v-bind="attrs"
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
        </template>
      </ConfirmPopover>
      <ConfirmPopover
        v-if="fiatQuestion"
        tone="warning"
        :title="fiatQuestion.title"
        :message="fiatQuestion.message"
        :confirm-label="t('asset_movement_matching.dialog.ignore')"
        @confirm="startPromise(ignoreAllFiat())"
      >
        <template #activator="{ attrs }">
          <RuiTooltip
            :open-delay="400"
            :options="{ placement: 'top' }"
            :class-names="{ tooltip: 'max-w-80' }"
          >
            <template #activator>
              <RuiButton
                variant="outlined"
                color="warning"
                :size="buttonSize"
                class="rounded-l-none -ml-px"
                :class="{ 'h-7.5': isPinned }"
                :disabled="bulkGated || fiatCount === 0 || ignoreLoading"
                :loading="ignoreLoading"
                data-testid="ignore-fiat"
                v-bind="attrs"
              >
                {{ t('asset_movement_matching.actions.ignore_fiat') }}
              </RuiButton>
            </template>
            {{ t('asset_movement_matching.actions.ignore_fiat_tooltip') }}
          </RuiTooltip>
        </template>
      </ConfirmPopover>
      <RuiButtonGroup
        color="primary"
        :class="autoMatchGroupClass"
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
              :disabled="!isAutoMatchAllowed || unmatched.length === 0 || autoMatchLoading"
              :loading="autoMatchLoading"
              data-testid="auto-match"
              @click="autoMatch()"
            >
              {{ t('asset_movement_matching.actions.auto_match') }}
            </RuiButton>
          </template>
          {{ t(kind.messages.autoMatchTooltip) }}
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
        v-if="showRestoreSelected"
        variant="outlined"
        color="primary"
        :size="buttonSize"
        :disabled="bulkGated || modelSelectedIgnored.length === 0 || ignoreLoading"
        :loading="ignoreLoading"
        data-testid="restore-selected"
        @click="restoreSelected()"
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
