<script setup lang="ts">
import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';
import { DuplicatesTab } from '@/modules/history/events/use-customized-event-duplicates-dialog';
import { useDuplicatesQuestion } from '@/modules/history/events/use-duplicates-question';
import ConfirmPopover from '@/modules/shell/components/ConfirmPopover.vue';

/**
 * The duplicates dialog's bulk actions for the tab being viewed. Each asks beside its button, so an
 * emitted action means the user accepted it for the counted selection.
 */
const { activeTab, autoFixCount, fixLoading = false, ignoredCount, ignoreLoading = false, manualReviewCount } = defineProps<{
  activeTab: number;
  /** How many groups each tab has selected. */
  autoFixCount: number;
  manualReviewCount: number;
  ignoredCount: number;
  fixLoading?: boolean;
  ignoreLoading?: boolean;
}>();

const emit = defineEmits<{
  'fix-selected': [];
  'ignore-selected': [];
  'restore-selected': [];
  'close': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const questions = useDuplicatesQuestion();

/** Marking non-duplicated acts on whichever of the two reviewable tabs is shown. */
const ignoreCount = computed<number>(() => activeTab === DuplicatesTab.AUTO_FIX ? autoFixCount : manualReviewCount);

const fixQuestion = computed<ConfirmQuestion>(() => questions.fixQuestion(autoFixCount));
const ignoreQuestion = computed<ConfirmQuestion>(() => questions.markNonDuplicatedQuestion(get(ignoreCount)));
const restoreQuestion = computed<ConfirmQuestion>(() => questions.restoreQuestion(ignoredCount));
</script>

<template>
  <div class="w-full flex justify-between gap-2 pb-4">
    <div
      v-if="activeTab === DuplicatesTab.IGNORED"
      class="flex gap-2"
    >
      <ConfirmPopover
        :question="restoreQuestion"
        @confirm="emit('restore-selected')"
      >
        <template #activator="{ attrs }">
          <RuiButton
            variant="outlined"
            color="primary"
            data-testid="restore-selected"
            :disabled="ignoredCount === 0 || ignoreLoading"
            :loading="ignoreLoading"
            v-bind="attrs"
          >
            <template #prepend>
              <RuiIcon
                size="16"
                name="lu-rotate-ccw"
              />
            </template>
            {{ t('customized_event_duplicates.actions.restore_selected') }}
            <RuiChip
              v-if="ignoredCount > 0"
              size="sm"
              color="primary"
              class="ml-2 py-0!"
            >
              {{ ignoredCount }}
            </RuiChip>
          </RuiButton>
        </template>
      </ConfirmPopover>
    </div>
    <div
      v-else
      class="flex gap-2"
    >
      <ConfirmPopover
        v-if="activeTab === DuplicatesTab.AUTO_FIX"
        :question="fixQuestion"
        @confirm="emit('fix-selected')"
      >
        <template #activator="{ attrs }">
          <RuiButton
            variant="outlined"
            color="primary"
            data-testid="fix-selected"
            :disabled="autoFixCount === 0 || fixLoading"
            :loading="fixLoading"
            v-bind="attrs"
          >
            <template #prepend>
              <RuiIcon
                size="16"
                name="lu-wand-sparkles"
              />
            </template>
            {{ t('customized_event_duplicates.actions.fix_selected') }}
            <RuiChip
              v-if="autoFixCount > 0"
              size="sm"
              color="primary"
              class="ml-2 py-0!"
            >
              {{ autoFixCount }}
            </RuiChip>
          </RuiButton>
        </template>
      </ConfirmPopover>
      <ConfirmPopover
        :question="ignoreQuestion"
        @confirm="emit('ignore-selected')"
      >
        <template #activator="{ attrs }">
          <RuiButton
            variant="outlined"
            data-testid="ignore-selected"
            :disabled="ignoreCount === 0 || ignoreLoading"
            :loading="ignoreLoading"
            v-bind="attrs"
          >
            <template #prepend>
              <RuiIcon
                size="16"
                name="lu-eye-off"
              />
            </template>
            {{ t('customized_event_duplicates.actions.mark_non_duplicated_selected') }}
            <RuiChip
              v-if="activeTab === DuplicatesTab.MANUAL_REVIEW && ignoreCount > 0"
              size="sm"
              color="primary"
              class="ml-2 py-0!"
            >
              {{ ignoreCount }}
            </RuiChip>
          </RuiButton>
        </template>
      </ConfirmPopover>
    </div>
    <RuiButton
      variant="text"
      data-testid="close-dialog"
      @click="emit('close')"
    >
      {{ t('common.actions.close') }}
    </RuiButton>
  </div>
</template>
