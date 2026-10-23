<script setup lang="ts">
import type { SetAside } from '@/modules/shell/action-center/use-action-center-snooze';
import { startPromise } from '@shared/utils';
import MissingPricesDialog from '@/modules/assets/prices/missing/MissingPricesDialog.vue';
import { useMissingPrices } from '@/modules/assets/prices/missing/use-missing-prices';
import { useMissingPricesDialog } from '@/modules/assets/prices/missing/use-missing-prices-dialog';
import ActionCenterList from '@/modules/core/action-center/ActionCenterList.vue';
import ActionCenterMenu from '@/modules/core/action-center/ActionCenterMenu.vue';
import { useOpenActionTarget } from '@/modules/core/action-center/use-open-action-target';
import ActionCenterSetAsideFilters from '@/modules/shell/action-center/ActionCenterSetAsideFilters.vue';
import { useActionCenterFolds } from '@/modules/shell/action-center/use-action-center-folds';
import { useGlobalActionCenter } from '@/modules/shell/action-center/use-global-action-center';

const open = ref<boolean>(false);
const revealed = ref<SetAside[]>([]);

const { awaitingFirstScan, cleared, count, markSeen, newCount, newIds, previousCounts, refreshAll, refreshing, sections, setAsideCounts, urgency } = useGlobalActionCenter({ revealed });
const { modelFolded } = useActionCenterFolds();
const { openTarget } = useOpenActionTarget();
const { missingPriceIdentifiers } = useMissingPrices();
const { modelOpen: missingPricesOpen } = useMissingPricesDialog();

function close(): void {
  set(open, false);
}

// Marking on close rather than on open keeps the new markers up while the user reads them.
watch(open, (isOpen, wasOpen) => {
  if (wasOpen && !isOpen) {
    markSeen();
    set(revealed, []);
  }
});
</script>

<template>
  <ActionCenterMenu
    v-model="open"
    :count="count"
    :new-count="newCount"
    :urgency="urgency"
    :checking="awaitingFirstScan"
    badge
  >
    <ActionCenterList
      v-model:folded="modelFolded"
      :sections="sections"
      :cleared="cleared"
      :count="count"
      :new-ids="newIds"
      :previous-counts="previousCounts"
      :checking="awaitingFirstScan"
      :refreshing="refreshing"
      @open="openTarget($event, close)"
      @refresh="startPromise(refreshAll())"
    >
      <template #header-actions>
        <ActionCenterSetAsideFilters
          v-model:revealed="revealed"
          :counts="setAsideCounts"
        />
      </template>
    </ActionCenterList>
  </ActionCenterMenu>
  <MissingPricesDialog
    v-if="missingPricesOpen"
    v-model:open="missingPricesOpen"
    :identifiers="missingPriceIdentifiers"
  />
</template>
