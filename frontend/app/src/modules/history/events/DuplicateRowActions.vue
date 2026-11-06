<script setup lang="ts">
import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';
import { useDuplicatesQuestion } from '@/modules/history/events/use-duplicates-question';
import ConfirmPopover from '@/modules/shell/components/ConfirmPopover.vue';

/** Each action asks beside its button, so `fix`, `ignore` and `restore` mean the user accepted. */
const { fixLoading, ignoreLoading, mode } = defineProps<{
  mode: 'auto-fix' | 'manual-review' | 'ignored';
  fixLoading?: boolean;
  ignoreLoading?: boolean;
}>();

const emit = defineEmits<{
  fix: [];
  ignore: [];
  restore: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const questions = useDuplicatesQuestion();

const fixQuestion = computed<ConfirmQuestion>(() => questions.fixQuestion(1));
const ignoreQuestion = computed<ConfirmQuestion>(() => questions.markNonDuplicatedQuestion(1));
const restoreQuestion = computed<ConfirmQuestion>(() => questions.restoreQuestion(1));
</script>

<template>
  <div class="flex items-center gap-2">
    <ConfirmPopover
      v-if="mode === 'auto-fix'"
      :question="fixQuestion"
      @confirm="emit('fix')"
    >
      <template #activator="{ attrs }">
        <RuiButton
          size="sm"
          color="primary"
          :loading="fixLoading"
          data-testid="duplicate-row-fix"
          v-bind="attrs"
        >
          <template #prepend>
            <RuiIcon
              size="16"
              name="lu-wand-sparkles"
            />
          </template>
          {{ t('customized_event_duplicates.actions.fix') }}
        </RuiButton>
      </template>
    </ConfirmPopover>
    <ConfirmPopover
      v-if="mode === 'ignored'"
      :question="restoreQuestion"
      @confirm="emit('restore')"
    >
      <template #activator="{ attrs }">
        <RuiTooltip
          :open-delay="400"
          :options="{ placement: 'top' }"
        >
          <template #activator>
            <RuiButton
              size="sm"
              color="primary"
              :loading="ignoreLoading"
              data-testid="duplicate-row-restore"
              v-bind="attrs"
            >
              <template #prepend>
                <RuiIcon
                  size="16"
                  name="lu-rotate-ccw"
                />
              </template>
              {{ t('customized_event_duplicates.actions.restore') }}
            </RuiButton>
          </template>
          {{ t('customized_event_duplicates.actions.restore_tooltip') }}
        </RuiTooltip>
      </template>
    </ConfirmPopover>
    <ConfirmPopover
      v-else
      :question="ignoreQuestion"
      @confirm="emit('ignore')"
    >
      <template #activator="{ attrs }">
        <RuiTooltip
          :open-delay="400"
          :options="{ placement: 'top' }"
        >
          <template #activator>
            <RuiButton
              size="sm"
              variant="outlined"
              :loading="ignoreLoading"
              data-testid="duplicate-row-ignore"
              v-bind="attrs"
            >
              <template #prepend>
                <RuiIcon
                  size="16"
                  name="lu-eye-off"
                />
              </template>
              {{ t('customized_event_duplicates.actions.mark_non_duplicated') }}
            </RuiButton>
          </template>
          {{ t('customized_event_duplicates.actions.mark_non_duplicated_tooltip') }}
        </RuiTooltip>
      </template>
    </ConfirmPopover>
  </div>
</template>
