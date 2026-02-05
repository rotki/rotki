<script setup lang="ts">
import { useCustomizedEventDuplicates } from '@/composables/history/events/use-customized-event-duplicates';
import { type DuplicateHandlingStatus, DuplicateHandlingStatus as DuplicateStatus } from '@/composables/history/events/use-history-events-filters';
import { useConfirmStore } from '@/store/confirm';

const props = defineProps<{
  groupIdentifiers?: string[];
  duplicateHandlingStatus?: DuplicateHandlingStatus;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const route = useRoute();
const { show } = useConfirmStore();
const {
  autoFixGroupIds,
  fixDuplicates,
  fixLoading,
  manualReviewGroupIds,
} = useCustomizedEventDuplicates();

const { duplicateHandlingStatus, groupIdentifiers } = toRefs(props);

const isAutoFixable = computed<boolean>(() => get(duplicateHandlingStatus) === DuplicateStatus.AUTO_FIX);

const hasGroupIdentifiers = computed<boolean>(() => {
  const ids = get(groupIdentifiers);
  return !!ids && ids.length > 0;
});

const duplicateChipText = computed<string>(() => {
  if (get(isAutoFixable))
    return t('customized_event_duplicates.chips.viewing_auto_fixable');
  return t('customized_event_duplicates.chips.viewing_manual_review');
});

// Track the current valid group IDs from the composable
const currentValidGroupIds = computed<string[]>(() =>
  get(isAutoFixable) ? get(autoFixGroupIds) : get(manualReviewGroupIds),
);

// Calculate the difference between URL params and current valid IDs
const duplicateChanges = computed<{ resolved: number; added: number; remaining: string[] }>(() => {
  const urlIds = get(groupIdentifiers) ?? [];
  const validIds = get(currentValidGroupIds);

  if (urlIds.length === 0)
    return { added: 0, remaining: [], resolved: 0 };

  const remaining = urlIds.filter(id => validIds.includes(id));
  const resolved = urlIds.length - remaining.length;
  const added = validIds.filter(id => !urlIds.includes(id)).length;

  return { added, remaining, resolved };
});

const hasDuplicateChanges = computed<boolean>(() => {
  const { added, resolved } = get(duplicateChanges);
  return resolved > 0 || added > 0;
});

const allDuplicatesResolved = computed<boolean>(() => {
  const { remaining } = get(duplicateChanges);
  return get(hasGroupIdentifiers) && remaining.length === 0;
});

const duplicateChangesMessage = computed<string>(() => {
  const { added, resolved } = get(duplicateChanges);

  if (get(allDuplicatesResolved))
    return t('customized_event_duplicates.chips.all_resolved');

  const messages: string[] = [];
  if (resolved > 0)
    messages.push(t('customized_event_duplicates.chips.resolved_count', { count: resolved }));

  if (added > 0)
    messages.push(t('customized_event_duplicates.chips.added_count', { count: added }));

  return messages.join(' ');
});

function removeMissingAcquisitionParam(): void {
  const query = { ...route.query };
  delete query.missingAcquisitionIdentifier;
  router.push({ query });
}

function removeNegativeBalanceParam(): void {
  const query = { ...route.query };
  delete query.highlightedNegativeBalanceEvent;
  delete query.targetGroupIdentifier;
  router.push({ query });
}

function removeDuplicateEventsParam(): void {
  const query = { ...route.query };
  delete query.groupIdentifiers;
  delete query.duplicateHandlingStatus;
  router.push({ query });
}

async function fixDuplicateEvent(): Promise<void> {
  const ids = get(groupIdentifiers);
  if (!ids || ids.length === 0)
    return;

  const result = await fixDuplicates(ids);
  if (result.success) {
    removeDuplicateEventsParam();
    emit('refresh');
  }
}

function confirmFixDuplicate(): void {
  const count = get(groupIdentifiers)?.length ?? 0;
  show({
    message: t('customized_event_duplicates.actions.fix_selected_confirm', { count }),
    primaryAction: t('common.actions.confirm'),
    title: t('customized_event_duplicates.actions.fix_selected'),
  }, async () => fixDuplicateEvent());
}

function refreshDuplicateView(): void {
  const validIds = get(currentValidGroupIds);

  if (validIds.length === 0) {
    removeDuplicateEventsParam();
  }
  else {
    const query = { ...route.query, groupIdentifiers: validIds.join(',') };
    router.replace({ query });
  }
  emit('refresh');
}
</script>

<template>
  <div>
    <div
      v-if="route.query.missingAcquisitionIdentifier"
      class="mb-4"
    >
      <RuiChip
        closeable
        color="primary"
        size="sm"
        variant="outlined"
        @click:close="removeMissingAcquisitionParam()"
      >
        {{ t('transactions.events.show_missing_acquisition') }}
      </RuiChip>
    </div>

    <RuiTooltip
      v-if="route.query.highlightedNegativeBalanceEvent"
      class="mb-4"
      :popper="{ placement: 'bottom' }"
      :open-delay="400"
      tooltip-class="max-w-80"
    >
      <template #activator>
        <RuiChip
          closeable
          color="error"
          size="sm"
          variant="outlined"
          @click:close="removeNegativeBalanceParam()"
        >
          {{ t('transactions.events.show_negative_balance') }}
        </RuiChip>
      </template>
      {{ t('historical_balances.negative_balances.view_event_tooltip') }}
    </RuiTooltip>

    <div
      v-if="hasGroupIdentifiers"
      class="mb-4"
    >
      <RuiChip
        closeable
        color="warning"
        size="sm"
        variant="outlined"
        @click:close="removeDuplicateEventsParam()"
      >
        <div class="flex gap-1">
          {{ duplicateChipText }}

          <RuiButton
            v-if="isAutoFixable && !hasDuplicateChanges"
            size="sm"
            variant="text"
            class="!py-0 underline !text-xs gap-1"
            color="primary"
            :loading="fixLoading"
            @click="confirmFixDuplicate()"
          >
            <template #prepend>
              <RuiIcon
                name="lu-wand-sparkles"
                size="10"
              />
            </template>
            {{ t('customized_event_duplicates.actions.fix_all_shown') }}
          </RuiButton>
        </div>
      </RuiChip>

      <div
        v-if="hasDuplicateChanges"
        class="mt-1 flex items-center gap-1 text-xs text-rui-secondary"
      >
        <RuiIcon
          name="lu-info"
          size="16"
        />
        <span>{{ duplicateChangesMessage }}</span>
        <RuiButton
          size="sm"
          variant="text"
          color="secondary"
          class="!py-0 underline"
          @click="refreshDuplicateView()"
        >
          {{ allDuplicatesResolved ? t('customized_event_duplicates.chips.clear_filter') : t('common.refresh') }}
        </RuiButton>
      </div>
    </div>
  </div>
</template>
