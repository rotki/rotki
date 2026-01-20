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

function removeIdentifierParam(): void {
  const query = { ...route.query };
  delete query.identifiers;
  router.push({ query });
}

function removeNegativeBalanceParam(): void {
  const query = { ...route.query };
  delete query.negativeBalanceGroup;
  delete query.negativeBalanceEvent;
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

function updateDuplicateParams(validGroupIds: string[]): void {
  if (validGroupIds.length === 0) {
    removeDuplicateEventsParam();
  }
  else {
    const query = { ...route.query, groupIdentifiers: validGroupIds.join(',') };
    router.replace({ query });
  }
}

// Watch for changes in the duplicate group IDs and validate URL params
watch([autoFixGroupIds, manualReviewGroupIds], () => {
  const currentIds = get(groupIdentifiers);

  if (!currentIds || currentIds.length === 0)
    return;

  const validGroupIds = get(isAutoFixable) ? get(autoFixGroupIds) : get(manualReviewGroupIds);
  const remainingIds = currentIds.filter(id => validGroupIds.includes(id));

  if (remainingIds.length !== currentIds.length)
    updateDuplicateParams(remainingIds);
});
</script>

<template>
  <div
    v-if="route.query.identifiers"
    class="mb-4"
  >
    <RuiChip
      closeable
      color="primary"
      size="sm"
      variant="outlined"
      @click:close="removeIdentifierParam()"
    >
      {{ t('transactions.events.show_missing_acquisition') }}
    </RuiChip>
  </div>

  <RuiTooltip
    v-if="route.query.negativeBalanceGroup"
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
    class="mb-4 flex items-center gap-2"
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
          v-if="isAutoFixable"
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
  </div>
</template>
