<script setup lang="ts">
import type { InternalTxConflict } from './types';
import InternalTxConflictRepullSettings from '@/components/settings/general/InternalTxConflictRepullSettings.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import { useAreaVisibilityStore } from '@/modules/common/use-area-visibility-store';
import { PinnedNames } from '@/modules/session/types';
import InternalTxConflictsContent from './InternalTxConflictsContent.vue';

const modelValue = defineModel<boolean>({ default: false });

const { t } = useI18n({ useScope: 'global' });

const showSettings = ref<boolean>(false);
const { pinned } = storeToRefs(useAreaVisibilityStore());

function closeDialog(): void {
  set(modelValue, false);
}

function pinSection(): void {
  set(pinned, {
    name: PinnedNames.INTERNAL_TX_CONFLICTS,
    props: {},
  });
  closeDialog();
}

function showInEvents(conflict: InternalTxConflict): void {
  if (!conflict.groupIdentifier)
    return;

  set(pinned, {
    name: PinnedNames.INTERNAL_TX_CONFLICTS,
    props: { highlightedGroupIdentifier: conflict.groupIdentifier, highlightedTxHash: conflict.txHash },
  });
  closeDialog();
}
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
          <div>
            <CardTitle>
              {{ t('internal_tx_conflicts.dialog.title') }}
            </CardTitle>
            <p class="text-body-2 text-rui-text-secondary mt-1">
              {{ t('internal_tx_conflicts.dialog.description') }}
            </p>
          </div>
          <div class="flex items-center gap-1">
            <RuiTooltip
              :popper="{ placement: 'bottom' }"
              :open-delay="400"
            >
              <template #activator>
                <RuiButton
                  variant="text"
                  icon
                  @click="showSettings = !showSettings"
                >
                  <RuiIcon name="lu-settings" />
                </RuiButton>
              </template>
              {{ t('internal_tx_conflicts.actions.settings') }}
            </RuiTooltip>
            <RuiTooltip
              :popper="{ placement: 'bottom' }"
              :open-delay="400"
            >
              <template #activator>
                <RuiButton
                  variant="text"
                  icon
                  @click="pinSection()"
                >
                  <RuiIcon name="lu-pin" />
                </RuiButton>
              </template>
              {{ t('internal_tx_conflicts.actions.pin') }}
            </RuiTooltip>
            <RuiButton
              variant="text"
              icon
              @click="closeDialog()"
            >
              <RuiIcon name="lu-x" />
            </RuiButton>
          </div>
        </div>
      </template>

      <div
        v-if="showSettings"
        class="px-4 pt-4 border-b border-default"
      >
        <InternalTxConflictRepullSettings compact />
      </div>

      <InternalTxConflictsContent
        class="my-4"
        @show-in-events="showInEvents($event)"
      />

      <div class="w-full flex justify-end pb-4">
        <RuiButton
          variant="text"
          @click="closeDialog()"
        >
          {{ t('common.actions.close') }}
        </RuiButton>
      </div>
    </RuiCard>
  </RuiDialog>
</template>
