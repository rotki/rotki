<script setup lang="ts">
import { startPromise } from '@shared/utils';
import MissingPricesDialog from '@/modules/assets/prices/missing/MissingPricesDialog.vue';
import { useMissingPrices } from '@/modules/assets/prices/missing/use-missing-prices';
import { useMissingPricesDialog } from '@/modules/assets/prices/missing/use-missing-prices-dialog';
import ActionCenterList from '@/modules/core/action-center/ActionCenterList.vue';
import ActionCenterMenu from '@/modules/core/action-center/ActionCenterMenu.vue';
import { useOpenActionTarget } from '@/modules/core/action-center/use-open-action-target';
import { useGlobalActionCenter } from '@/modules/shell/action-center/use-global-action-center';

const open = ref<boolean>(false);

const { checking, cleared, count, markSeen, newCount, newIds, refreshAll, refreshing, sections } = useGlobalActionCenter();
const { openTarget } = useOpenActionTarget();
const { missingPriceIdentifiers } = useMissingPrices();
const { modelOpen: missingPricesOpen } = useMissingPricesDialog();

function close(): void {
  set(open, false);
}

// Marking on close rather than on open keeps the new markers up while the user reads them.
watch(open, (isOpen, wasOpen) => {
  if (wasOpen && !isOpen)
    markSeen();
});
</script>

<template>
  <ActionCenterMenu
    v-model="open"
    :count="count"
    :new-count="newCount"
    :checking="checking"
    badge
  >
    <ActionCenterList
      :sections="sections"
      :cleared="cleared"
      :count="count"
      :new-ids="newIds"
      :checking="checking"
      :refreshing="refreshing"
      @open="openTarget($event, close)"
      @refresh="startPromise(refreshAll())"
    />
  </ActionCenterMenu>
  <MissingPricesDialog
    v-if="missingPricesOpen"
    v-model:open="missingPricesOpen"
    :identifiers="missingPriceIdentifiers"
  />
</template>
