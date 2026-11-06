<script setup lang="ts">
import { useRestoreAssetDb } from '@/modules/assets/admin/use-restore-asset-db';
import ConfirmPopover from '@/modules/shell/components/ConfirmPopover.vue';
import InlineConfirm from '@/modules/shell/components/InlineConfirm.vue';
import ListItem from '@/modules/shell/components/ListItem.vue';

type ResetType = 'soft' | 'hard';

/**
 * Offers the soft and hard resets of the assets database, each asking before it runs.
 *
 * @remarks
 * `dropdown` renders the resets as entries of the menu this sits in. They expand in place rather
 * than in a nested menu: a nested menu is teleported out of its parent, so a click on it closes the
 * parent and would drop the question with it.
 */
const { dropdown = false } = defineProps<{
  dropdown?: boolean;
}>();

const emit = defineEmits<{
  /** The dropdown form started a reset, so the menu holding it can close. */
  close: [];
}>();

const { t } = useI18n({ useScope: 'global' });

/** Whether the dropdown form shows its two resets. */
const expanded = ref<boolean>(false);
/** The reset the dropdown form is asking about in place of its entries. */
const pendingType = ref<ResetType>();

const { loading, restoreAssets, restoreQuestion } = useRestoreAssetDb();

const softQuestion = computed<{ title: string; message: string }>(() => restoreQuestion('soft'));
const hardQuestion = computed<{ title: string; message: string }>(() => restoreQuestion('hard'));
const pendingQuestion = computed<{ title: string; message: string } | undefined>(() => {
  const type = get(pendingType);
  return type ? restoreQuestion(type) : undefined;
});

function resetDropdown(): void {
  set(pendingType, undefined);
  set(expanded, false);
}

async function acceptPending(): Promise<void> {
  const type = get(pendingType);
  resetDropdown();
  emit('close');
  if (type)
    await restoreAssets(type);
}
</script>

<template>
  <div
    v-if="dropdown"
    class="flex flex-col"
  >
    <InlineConfirm
      v-if="pendingQuestion"
      class="w-72"
      layout="panel"
      tone="error"
      :title="pendingQuestion.title"
      :message="pendingQuestion.message"
      :confirm-label="pendingType === 'soft' ? t('asset_update.restore.soft_reset') : t('asset_update.restore.hard_reset')"
      @cancel="resetDropdown()"
      @confirm="acceptPending()"
    />
    <template v-else>
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
          @click="pendingType = 'soft'"
        />
        <ListItem
          class="pl-8!"
          :title="t('asset_update.restore.hard_reset')"
          :subtitle="t('asset_update.restore.hard_reset_hint')"
          data-testid="asset-db-hard-reset-item"
          @click="pendingType = 'hard'"
        />
      </template>
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
        :title="softQuestion.title"
        :message="softQuestion.message"
        :confirm-label="t('asset_update.restore.soft_reset')"
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
        :title="hardQuestion.title"
        :message="hardQuestion.message"
        :confirm-label="t('asset_update.restore.hard_reset')"
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
