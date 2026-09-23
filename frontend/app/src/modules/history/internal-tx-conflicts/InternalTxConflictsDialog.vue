<script setup lang="ts">
import type { InternalTxConflict } from './types';
import InternalTxConflictsDialogHeaderActions from '@/modules/history/internal-tx-conflicts/InternalTxConflictsDialogHeaderActions.vue';
import { PinnedNames } from '@/modules/session/types';
import InternalTxConflictRepullSettings from '@/modules/settings/general/InternalTxConflictRepullSettings.vue';
import CardTitle from '@/modules/shell/components/CardTitle.vue';
import { usePinnedPanel } from '@/modules/shell/pinned/use-pinned-panel';
import InternalTxConflictsContent from './InternalTxConflictsContent.vue';

const modelValue = defineModel<boolean>({ default: false });

const { t } = useI18n({ useScope: 'global' });

const showSettings = ref<boolean>(false);
const { pin } = usePinnedPanel(PinnedNames.INTERNAL_TX_CONFLICTS);

function closeDialog(): void {
  set(modelValue, false);
}

function pinSection(): void {
  pin({});
  closeDialog();
}

function showInEvents(conflict: InternalTxConflict): void {
  if (!conflict.groupIdentifier)
    return;

  pin({ highlightedGroupIdentifier: conflict.groupIdentifier, highlightedTxHash: conflict.txHash });
  closeDialog();
}
</script>

<template>
  <RuiDialog
    v-model="modelValue"
    max-width="1000"
  >
    <RuiCard
      class="max-h-[90vh] flex flex-col overflow-hidden"
      content-class="!py-0 flex flex-col flex-1 min-h-0 overflow-hidden"
      divide
      data-testid="internal-tx-conflicts-dialog"
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
          <InternalTxConflictsDialogHeaderActions
            @toggle-settings="showSettings = !showSettings"
            @pin="pinSection()"
            @close="closeDialog()"
          />
        </div>
      </template>

      <div
        v-if="showSettings"
        class="px-4 pt-4 border-b border-default shrink-0"
      >
        <InternalTxConflictRepullSettings compact />
      </div>

      <InternalTxConflictsContent
        class="my-4"
        @show-in-events="showInEvents($event)"
      />

      <div class="w-full flex justify-end pb-4 shrink-0">
        <RuiButton
          variant="text"
          data-testid="internal-tx-conflicts-dialog-close"
          @click="closeDialog()"
        >
          {{ t('common.actions.close') }}
        </RuiButton>
      </div>
    </RuiCard>
  </RuiDialog>
</template>
