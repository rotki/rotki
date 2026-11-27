<script setup lang="ts">
import { RuiChip, RuiIcon, type RuiIcons } from '@rotki/ui-library';
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import LoginActionAlert from '@/modules/auth/login/LoginActionAlert.vue';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

const emit = defineEmits<{ proceed: [approval: 'yes' | 'no'] }>();

const { t } = useI18n({ useScope: 'global' });

const { syncConflict } = storeToRefs(useSessionAuthStore());

interface Copy {
  key: 'local' | 'remote';
  icon: RuiIcons;
  label: string;
  timestamp: number;
  newer: boolean;
}

/** The two copies of the database side by side, with the newer one marked. */
const copies = computed<Copy[]>(() => {
  const conflict = get(syncConflict);
  if (!conflict?.payload)
    return [];

  const { localLastModified, remoteLastModified } = conflict.payload;
  return [
    {
      icon: 'lu-hard-drive',
      key: 'local',
      label: t('login.sync_error.local'),
      newer: localLastModified > remoteLastModified,
      timestamp: localLastModified,
    },
    {
      icon: 'lu-cloud',
      key: 'remote',
      label: t('login.sync_error.remote'),
      newer: remoteLastModified > localLastModified,
      timestamp: remoteLastModified,
    },
  ];
});
</script>

<template>
  <Transition name="bounce">
    <LoginActionAlert
      v-if="syncConflict"
      icon="lu-cloud-download"
      @cancel="emit('proceed', 'no')"
      @confirm="emit('proceed', 'yes')"
    >
      <template #title>
        {{ t('login.sync_error.title') }}
      </template>
      <template #confirm>
        {{ t('login.sync_error.actions.use_remote') }}
      </template>
      <template #cancel>
        {{ t('login.sync_error.actions.keep_local') }}
      </template>

      <p class="break-words">
        {{ syncConflict.message }}
      </p>
      <dl
        v-if="copies.length > 0"
        class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 items-center py-1"
      >
        <template
          v-for="copy in copies"
          :key="copy.key"
        >
          <dt class="flex items-center gap-2 font-medium">
            <RuiIcon
              :name="copy.icon"
              size="16"
              class="shrink-0"
            />
            {{ copy.label }}
          </dt>
          <dd
            class="flex flex-wrap items-center gap-2 tabular-nums"
            :data-testid="`sync-conflict-${copy.key}`"
          >
            <DateDisplay :timestamp="copy.timestamp" />
            <RuiChip
              v-if="copy.newer"
              size="sm"
              color="primary"
              variant="outlined"
            >
              {{ t('login.sync_error.newer') }}
            </RuiChip>
          </dd>
        </template>
      </dl>
      <p>{{ t('login.sync_error.question') }}</p>
    </LoginActionAlert>
  </Transition>
</template>
