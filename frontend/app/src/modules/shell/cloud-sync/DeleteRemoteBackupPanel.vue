<script setup lang="ts">
import { RuiButton, RuiCheckbox, RuiIcon, type RuiIcons, RuiSkeletonLoader } from '@rotki/ui-library';
import { watchImmediate } from '@vueuse/core';
import { get, set } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, onBeforeMount, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { size } from '@/modules/core/common/data/data';
import { usePremiumStore } from '@/modules/premium/use-premium-store';
import { RemoteBackupDeletionPhase, useRemoteBackupDeletion } from '@/modules/shell/cloud-sync/use-remote-backup-deletion';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import TimeAgoDisplay from '@/modules/shell/components/display/TimeAgoDisplay.vue';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';

/**
 * Deletes the backup stored on the rotki server, in place inside the sync menu like the sync
 * confirmation. It first shows which backup that is, and says the local database is not touched:
 * a user reaching for this may fear for the data on this device.
 *
 * It is mounted only while shown, so every opening asks the server again.
 */
const busy = defineModel<boolean>('busy', { default: false });

const emit = defineEmits<{
  close: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { premiumSync } = storeToRefs(usePremiumStore());

interface Outcome {
  icon: RuiIcons;
  iconClass: string;
  title: string;
  message?: string;
  testId: string;
}

const { backup, backupChanged, failure, load, phase, remove } = useRemoteBackupDeletion();

const disableSync = ref<boolean>(true);
/** Whether automatic backup was on when the deletion started, to say if the deletion turned it off. */
const syncWasOn = ref<boolean>(false);

const loading = computed<boolean>(() => get(phase) === RemoteBackupDeletionPhase.LOADING);

const deleting = computed<boolean>(() => get(phase) === RemoteBackupDeletionPhase.DELETING);

/** Asking the server, reviewing or deleting: the confirmation is up. */
const confirming = computed<boolean>(() => get(loading) || get(deleting) || get(phase) === RemoteBackupDeletionPhase.REVIEW);

const canDelete = computed<boolean>(() => get(phase) === RemoteBackupDeletionPhase.REVIEW);

function deletedMessage(): string {
  if (get(premiumSync))
    return t('delete_remote_backup.deleted.sync_on');
  return get(syncWasOn) ? t('delete_remote_backup.deleted.sync_off') : t('delete_remote_backup.deleted.others');
}

/** The end states, where there is nothing left to do but close. */
const outcome = computed<Outcome | undefined>(() => {
  switch (get(phase)) {
    case RemoteBackupDeletionPhase.DELETED:
      return {
        icon: 'lu-circle-check',
        iconClass: 'text-rui-success',
        message: deletedMessage(),
        testId: 'delete-remote-backup-deleted',
        title: t('delete_remote_backup.deleted.title'),
      };
    case RemoteBackupDeletionPhase.EMPTY:
      return {
        icon: 'lu-cloud-off',
        iconClass: 'text-rui-text-secondary',
        testId: 'delete-remote-backup-empty',
        title: t('delete_remote_backup.empty'),
      };
    default:
      return undefined;
  }
});

async function confirm(): Promise<void> {
  set(syncWasOn, get(premiumSync));
  await remove(get(disableSync));
}

watchImmediate(deleting, (value) => {
  set(busy, value);
});

onBeforeMount(async () => load());
</script>

<template>
  <div
    class="flex flex-col gap-3 rounded-rui-control border p-3"
    :class="confirming ? 'border-rui-error/40 bg-rui-error/5' : 'border-default'"
    data-testid="delete-remote-backup"
  >
    <template v-if="confirming">
      <div class="flex gap-2">
        <RuiIcon
          name="lu-triangle-alert"
          size="18"
          class="text-rui-error shrink-0 mt-0.5"
        />
        <div class="flex flex-col gap-1 text-sm">
          <div class="font-medium text-rui-text">
            {{ t('delete_remote_backup.title') }}
          </div>
          <div class="text-rui-text-secondary">
            {{ t('delete_remote_backup.message') }}
          </div>
        </div>
      </div>

      <div
        v-if="backupChanged"
        class="text-xs text-rui-warning"
        data-testid="delete-remote-backup-changed"
      >
        {{ t('delete_remote_backup.changed') }}
      </div>

      <div
        class="flex items-center gap-2 border-t border-rui-error/20 pt-3"
        data-testid="delete-remote-backup-details"
      >
        <RuiIcon
          name="lu-cloud"
          size="18"
          class="text-rui-text-secondary shrink-0"
        />
        <div
          v-if="loading"
          class="flex grow flex-col gap-1.5 py-0.5"
          data-testid="delete-remote-backup-loading"
        >
          <RuiSkeletonLoader class="h-3.5 w-3/4" />
          <RuiSkeletonLoader class="h-3 w-1/2" />
        </div>
        <div
          v-else-if="backup"
          class="flex min-w-0 flex-col text-sm"
        >
          <DateDisplay
            :timestamp="backup.lastModifyTs"
            class="font-medium text-rui-text"
          />
          <div class="flex flex-wrap gap-x-1 text-xs text-rui-text-secondary">
            <span data-testid="delete-remote-backup-size">{{ size(backup.dataSize) }}</span>
            <span class="before:mr-1 before:content-['·']">{{ t('delete_remote_backup.uploaded') }}</span>
            <TimeAgoDisplay :timestamp="backup.uploadTs" />
          </div>
        </div>
      </div>

      <FailureStrip
        v-if="failure !== undefined"
        :title="t('delete_remote_backup.delete_failed')"
        :failure="failure"
        data-testid="delete-remote-backup-failure"
      />

      <RuiCheckbox
        v-if="premiumSync"
        v-model="disableSync"
        color="primary"
        size="sm"
        details="hidden"
        :disabled="!canDelete"
        data-testid="delete-remote-backup-disable-sync"
      >
        {{ t('delete_remote_backup.disable_sync') }}
      </RuiCheckbox>

      <div class="flex justify-end gap-2">
        <RuiButton
          variant="text"
          size="sm"
          :disabled="deleting"
          data-testid="delete-remote-backup-cancel"
          @click="emit('close')"
        >
          {{ t('common.actions.cancel') }}
        </RuiButton>
        <RuiButton
          color="error"
          size="sm"
          :disabled="!canDelete"
          :loading="deleting"
          data-testid="delete-remote-backup-confirm"
          @click="confirm()"
        >
          {{ t('delete_remote_backup.action') }}
        </RuiButton>
      </div>
    </template>

    <template v-else>
      <FailureStrip
        v-if="phase === RemoteBackupDeletionPhase.LOAD_FAILED"
        :title="backupChanged ? t('delete_remote_backup.changed_unloaded') : t('delete_remote_backup.load_failed')"
        :failure="failure"
        data-testid="delete-remote-backup-load-failed"
        @retry="load()"
      />
      <div
        v-else-if="outcome"
        class="flex gap-2"
        :data-testid="outcome.testId"
      >
        <RuiIcon
          :name="outcome.icon"
          size="18"
          class="shrink-0 mt-0.5"
          :class="outcome.iconClass"
        />
        <div class="flex flex-col gap-1 text-sm">
          <div class="font-medium text-rui-text">
            {{ outcome.title }}
          </div>
          <div
            v-if="outcome.message"
            class="text-rui-text-secondary"
          >
            {{ outcome.message }}
          </div>
        </div>
      </div>
      <div class="flex justify-end">
        <RuiButton
          variant="text"
          size="sm"
          data-testid="delete-remote-backup-close"
          @click="emit('close')"
        >
          {{ t('common.actions.done') }}
        </RuiButton>
      </div>
    </template>
  </div>
</template>
