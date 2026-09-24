<script setup lang="ts">
import type { ActivityId } from '@/modules/task-center/core/types';
import { Blockchain } from '@rotki/common';
import { addAccountLink } from '@/modules/accounts/add-account-link';
import { useTaskDock } from '@/modules/task-center/use-task-dock';

const { addresses, dismisses } = defineProps<{
  /** The addresses tracked nowhere, which the add dialog opens holding. */
  addresses: string[];
  /** The job the action answers, dismissed once the user acts on it; left alone for a leaf, whose job says more. */
  dismisses?: ActivityId;
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const { acknowledge, modelExpanded } = useTaskDock();

/**
 * Opens the add dialog on Ethereum rather than adding straight away: an address with no activity
 * anywhere may be meant for another chain, so the user confirms the chain instead of rotki guessing.
 */
async function track(): Promise<void> {
  if (dismisses)
    acknowledge(dismisses);
  set(modelExpanded, false);
  await router.push(addAccountLink({ addresses, chain: Blockchain.ETH }));
}
</script>

<template>
  <RuiButton
    class="self-start -ml-2"
    variant="text"
    color="primary"
    size="sm"
    data-testid="dock-track-action"
    @click="track()"
  >
    {{ t('task_dock.detail.addition.track_on_chain', { count: addresses.length }, addresses.length) }}
  </RuiButton>
</template>
