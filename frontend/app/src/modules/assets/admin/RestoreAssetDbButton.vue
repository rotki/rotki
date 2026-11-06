<script setup lang="ts">
import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';
import { startPromise } from '@shared/utils';
import { type ResetType, useRestoreAssetDb } from '@/modules/assets/admin/use-restore-asset-db';
import ConfirmPopover from '@/modules/shell/components/ConfirmPopover.vue';
import ListItem from '@/modules/shell/components/ListItem.vue';
import { useConfirmMenuAsk } from '@/modules/shell/components/use-confirm-menu';

/**
 * Offers the soft and hard resets of the assets database, each asking before it runs.
 *
 * @remarks
 * `dropdown` renders the resets as entries of the `ConfirmMenu` this sits in, which asks the question
 * and closes once it is accepted. They expand in place rather than in a nested menu: a nested menu is
 * teleported out of its parent, so a click on it closes the parent and would drop the question with
 * it.
 */
const { dropdown = false } = defineProps<{
  dropdown?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

/** Whether the dropdown form shows its two resets. */
const expanded = ref<boolean>(false);

const { loading, restoreAssets, restoreQuestion } = useRestoreAssetDb();
const askInMenu = useConfirmMenuAsk();

const softQuestion = computed<ConfirmQuestion>(() => restoreQuestion('soft'));
const hardQuestion = computed<ConfirmQuestion>(() => restoreQuestion('hard'));

/** Asks about a reset picked from the dropdown inside the menu holding it, then runs it. */
function pick(type: ResetType): void {
  askInMenu?.(restoreQuestion(type), () => {
    set(expanded, false);
    startPromise(restoreAssets(type));
  });
}
</script>

<template>
  <div
    v-if="dropdown"
    class="flex flex-col"
  >
    <RuiButton
      variant="list"
      :disabled="loading"
      :aria-expanded="expanded"
      data-testid="asset-db-reset-menu"
      @click="expanded = !expanded"
    >
      <template #prepend>
        <RuiIcon name="lu-rotate-ccw" />
      </template>
      {{ t('asset_update.restore.title') }}
      <template #append>
        <RuiIcon :name="expanded ? 'lu-chevron-up' : 'lu-chevron-down'" />
      </template>
    </RuiButton>
    <template v-if="expanded">
      <ListItem
        class="pl-8!"
        :title="t('asset_update.restore.soft_reset')"
        :subtitle="t('asset_update.restore.soft_reset_hint')"
        data-testid="asset-db-soft-reset-item"
        @click="pick('soft')"
      />
      <ListItem
        class="pl-8!"
        :title="t('asset_update.restore.hard_reset')"
        :subtitle="t('asset_update.restore.hard_reset_hint')"
        data-testid="asset-db-hard-reset-item"
        @click="pick('hard')"
      />
    </template>
  </div>
  <div
    v-else
    class="flex flex-col rounded-rui-card border border-rui-divider between:border-t between:border-rui-divider"
  >
    <div class="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 p-4">
      <div class="flex flex-col gap-0.5">
        <span class="text-sm font-medium text-rui-text">{{ t('asset_update.restore.soft_reset') }}</span>
        <span class="text-sm text-rui-text-secondary">{{ t('asset_update.restore.soft_reset_hint') }}</span>
      </div>
      <ConfirmPopover
        :question="softQuestion"
        @confirm="restoreAssets('soft')"
      >
        <template #activator="{ attrs }">
          <RuiButton
            variant="outlined"
            color="error"
            :loading="loading"
            data-testid="asset-db-soft-reset"
            v-bind="attrs"
          >
            {{ t('asset_update.restore.soft_reset') }}
          </RuiButton>
        </template>
      </ConfirmPopover>
    </div>
    <div class="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 p-4">
      <div class="flex flex-col gap-0.5">
        <span class="text-sm font-medium text-rui-text">{{ t('asset_update.restore.hard_reset') }}</span>
        <span class="text-sm text-rui-text-secondary">{{ t('asset_update.restore.hard_reset_hint') }}</span>
      </div>
      <ConfirmPopover
        :question="hardQuestion"
        @confirm="restoreAssets('hard')"
      >
        <template #activator="{ attrs }">
          <RuiButton
            color="error"
            :loading="loading"
            data-testid="asset-db-hard-reset"
            v-bind="attrs"
          >
            {{ t('asset_update.restore.hard_reset') }}
          </RuiButton>
        </template>
      </ConfirmPopover>
    </div>
  </div>
</template>
