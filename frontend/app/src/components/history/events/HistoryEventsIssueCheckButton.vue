<script setup lang="ts">
import { DIALOG_TYPES, type DialogShowOptions } from '@/components/history/events/dialog-types';
import { useCustomizedEventDuplicates } from '@/composables/history/events/use-customized-event-duplicates';
import { useUnmatchedAssetMovements } from '@/composables/history/events/use-unmatched-asset-movements';
import { useRefWithDebounce } from '@/composables/ref';
import { useStatusStore } from '@/store/status';
import { Section, Status } from '@/types/status';

const showAlerts = defineModel<boolean>('showAlerts', { default: false });

const props = defineProps<{
  processing: boolean;
  mainPage?: boolean;
}>();

const emit = defineEmits<{
  'show:dialog': [options: DialogShowOptions];
}>();

const { mainPage, processing } = toRefs(props);

const { t } = useI18n({ useScope: 'global' });
const { getStatus } = useStatusStore();

const checkingIssues = ref<boolean>(false);
const noIssuesFound = ref<boolean>(false);

const { autoMatchLoading, refreshUnmatchedAssetMovements, unmatchedCount } = useUnmatchedAssetMovements();
const { fetchCustomizedEventDuplicates, totalCount: duplicatesCount } = useCustomizedEventDuplicates();

const totalIssuesCount = computed<number>(() => get(unmatchedCount) + get(duplicatesCount));
const hasIssues = computed<boolean>(() => !get(autoMatchLoading) && get(totalIssuesCount) > 0);
const hasOnlyUnmatchedMovements = computed<boolean>(() => get(unmatchedCount) > 0 && get(duplicatesCount) === 0);

const debouncedProcessing = useRefWithDebounce(processing, 200);
const issueButtonEnabled = computed<boolean>(() => !get(debouncedProcessing) && getStatus(Section.HISTORY) === Status.LOADED);
const showWarningButton = logicAnd(issueButtonEnabled, mainPage, hasIssues);

const buttonColor = computed<'warning' | 'success' | 'primary'>(() => {
  if (!get(issueButtonEnabled))
    return 'primary';
  if (get(showWarningButton))
    return 'warning';
  if (get(noIssuesFound))
    return 'success';
  return 'primary';
});

const { start: startNoIssuesTimeout, stop: stopNoIssuesTimeout } = useTimeoutFn(() => {
  set(noIssuesFound, false);
}, 2000, { immediate: false });

function showNoIssuesFeedback(): void {
  stopNoIssuesTimeout();
  set(noIssuesFound, true);
  startNoIssuesTimeout();
}

function toggleAlerts(): void {
  if (get(hasOnlyUnmatchedMovements)) {
    emit('show:dialog', { type: DIALOG_TYPES.MATCH_ASSET_MOVEMENTS });
  }
  else {
    set(showAlerts, !get(showAlerts));
  }
}

function openAlertsIfNeeded(): void {
  if (!get(showWarningButton))
    return;

  if (get(hasOnlyUnmatchedMovements)) {
    emit('show:dialog', { type: DIALOG_TYPES.MATCH_ASSET_MOVEMENTS });
  }
  else {
    set(showAlerts, true);
  }
}

async function checkIssues(): Promise<void> {
  set(checkingIssues, true);
  try {
    await Promise.all([
      refreshUnmatchedAssetMovements(),
      fetchCustomizedEventDuplicates(),
    ]);
    openAlertsIfNeeded();
    if (!get(hasIssues))
      showNoIssuesFeedback();
  }
  finally {
    set(checkingIssues, false);
  }
}

async function checkUnmatched(): Promise<void> {
  set(checkingIssues, true);
  try {
    await refreshUnmatchedAssetMovements();
    emit('show:dialog', { type: DIALOG_TYPES.MATCH_ASSET_MOVEMENTS });
  }
  finally {
    set(checkingIssues, false);
  }
}

async function checkDuplicates(): Promise<void> {
  set(checkingIssues, true);
  try {
    await fetchCustomizedEventDuplicates();
    if (get(duplicatesCount) > 0)
      set(showAlerts, true);
    else if (!get(hasIssues))
      showNoIssuesFeedback();
  }
  finally {
    set(checkingIssues, false);
  }
}

watch(showWarningButton, (value) => {
  if (!value)
    set(showAlerts, false);
});
</script>

<template>
  <RuiButtonGroup
    variant="outlined"
    :color="buttonColor"
    class="h-9 [&>div]:!border-none"
    :class="{ '!outline-rui-grey-500/[0.5]': !issueButtonEnabled }"
    :disabled="!issueButtonEnabled"
  >
    <RuiBadge
      v-if="showWarningButton"
      :model-value="totalIssuesCount > 0"
      :text="totalIssuesCount.toString()"
      color="warning"
      placement="top"
      offset-y="4"
      offset-x="-4"
    >
      <RuiButton
        variant="outlined"
        color="warning"
        class="rounded-r-none !outline-none !border-r"
        :class="issueButtonEnabled ? 'border-rui-warning/[0.5]' : 'border-rui-grey-500/[0.5]'"
        :disabled="!issueButtonEnabled"
        :loading="checkingIssues"
        @click="toggleAlerts()"
      >
        <template #prepend>
          <RuiIcon
            name="lu-triangle-alert"
            size="18"
          />
        </template>
        <span class="hidden md:inline">{{ t('transactions.alerts.button') }}</span>
        <template #append>
          <RuiIcon
            name="lu-chevron-down"
            size="16"
            class="transition-transform duration-200"
            :class="{ 'rotate-180': showAlerts }"
          />
        </template>
      </RuiButton>
    </RuiBadge>

    <RuiButton
      v-else
      variant="outlined"
      :color="issueButtonEnabled && noIssuesFound ? 'success' : 'primary'"
      :loading="checkingIssues"
      class="rounded-r-none !outline-none !border-r"
      :class="issueButtonEnabled && noIssuesFound ? 'border-rui-success/[0.5]' : 'border-rui-grey-600/[0.5]'"
      :disabled="!issueButtonEnabled"
      @click="checkIssues()"
    >
      <template #prepend>
        <RuiIcon
          :name="noIssuesFound ? 'lu-circle-check' : 'lu-search-check'"
          size="18"
        />
      </template>
      <span class="hidden md:inline">{{ noIssuesFound ? t('transactions.alerts.no_issues_found') : t('transactions.alerts.check_issues') }}</span>
    </RuiButton>

    <RuiMenu
      :popper="{ placement: 'bottom-end' }"
      menu-class="max-w-[24rem]"
      close-on-content-click
      :disabled="!issueButtonEnabled"
      wrapper-class="h-full"
    >
      <template #activator="{ attrs }">
        <RuiButton
          variant="outlined"
          :color="buttonColor"
          class="rounded-l-none !outline-none px-3 h-9"
          :disabled="!issueButtonEnabled"
          v-bind="attrs"
        >
          <RuiIcon
            name="lu-chevrons-up-down"
            size="16"
          />
        </RuiButton>
      </template>

      <div class="py-2">
        <RuiButton
          variant="list"
          @click="checkUnmatched()"
        >
          <template #prepend>
            <RuiIcon name="lu-git-compare-arrows" />
          </template>
          {{ t('transactions.alerts.check_unmatched_movements') }}
        </RuiButton>

        <RuiButton
          variant="list"
          @click="checkDuplicates()"
        >
          <template #prepend>
            <RuiIcon name="lu-copy" />
          </template>
          {{ t('transactions.alerts.check_duplicate_events') }}
        </RuiButton>
      </div>
    </RuiMenu>
  </RuiButtonGroup>
</template>
