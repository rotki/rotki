<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';
import type { BankConnection } from '@/modules/banks/types';
import { type MessageKey, msg } from '@/message-key';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import TimeAgoDisplay from '@/modules/shell/components/display/TimeAgoDisplay.vue';

const { connection } = defineProps<{ connection: BankConnection }>();

const emit = defineEmits<{
  /** syncing again is the way out of an expired TAN; the page that lists the connections runs it */
  sync: [connection: { identifier: string }];
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

type ConnectionState = 'authentication' | 'expired' | 'failed' | 'ok';

interface StatusDisplay {
  icon: RuiIcons;
  textClass: string;
  text: MessageKey;
  action: MessageKey;
}

/**
 * How each state shows, in the colour and icon every bank surface uses for it: a pending TAN cannot
 * wait, an expired one can.
 */
const STATUSES: Record<Exclude<ConnectionState, 'ok'>, StatusDisplay> = {
  authentication: {
    action: msg.$t('bank_balances.status.authenticate'),
    icon: 'lu-shield-alert',
    text: msg.$t('bank_balances.status.authentication'),
    textClass: 'text-rui-error',
  },
  expired: {
    action: msg.$t('bank_settings.authentication.sync_again'),
    icon: 'lu-shield-x',
    text: msg.$t('bank_balances.status.expired'),
    textClass: 'text-rui-warning',
  },
  failed: {
    action: msg.$t('bank_balances.status.review'),
    icon: 'lu-circle-alert',
    text: msg.$t('bank_balances.status.failed'),
    textClass: 'text-rui-error',
  },
};

/** A pending TAN outranks an older failure: answering it is what unblocks the connection. */
const state = computed<ConnectionState>(() => {
  if (connection.syncStatus.authChallenge)
    return 'authentication';
  if (connection.syncStatus.authExpired)
    return 'expired';
  if (connection.syncStatus.lastError)
    return 'failed';
  return 'ok';
});

const status = computed<StatusDisplay | undefined>(() => {
  const current = get(state);
  return current === 'ok' ? undefined : STATUSES[current];
});

/** Only a failure names a reason. */
const statusText = computed<string>(() => {
  const current = get(status);
  if (!current)
    return '';
  return get(state) === 'failed' ? t(current.text, { error: connection.syncStatus.lastError }) : t(current.text);
});

/** A pending TAN opens its answer, an expired one syncs again for a fresh TAN, a failure leads to the connection. */
async function act(): Promise<void> {
  const { identifier } = connection;
  if (get(state) === 'expired') {
    emit('sync', { identifier });
    return;
  }
  const query: Record<string, string> = get(state) === 'authentication' ? { authenticate: identifier } : {};
  await router.push({ name: '/api-keys/banks/', query });
}
</script>

<template>
  <li
    class="flex flex-wrap items-center gap-x-2 gap-y-1 min-w-0"
    data-testid="bank-balances-connection"
    :data-connection="connection.name"
    :data-state="state"
  >
    <LocationIcon
      :item="connection.location"
      icon
      size="20px"
    />
    <span class="text-body-2 font-medium truncate">{{ connection.name }}</span>
    <span class="text-caption text-rui-text-secondary shrink-0">{{ connection.displayName }}</span>

    <i18n-t
      v-if="state === 'ok' && connection.syncStatus.lastSyncTs"
      scope="global"
      keypath="bank_balances.status.synced"
      tag="span"
      class="text-caption text-rui-text-secondary"
      data-testid="bank-balances-connection-synced"
    >
      <template #time>
        <TimeAgoDisplay :timestamp="connection.syncStatus.lastSyncTs" />
      </template>
    </i18n-t>

    <template v-if="status">
      <span
        class="flex items-center gap-1 text-caption min-w-0"
        :class="status.textClass"
        data-testid="bank-balances-connection-status"
      >
        <RuiIcon
          :name="status.icon"
          size="14"
          class="shrink-0"
        />
        <span class="truncate">
          {{ statusText }}
        </span>
      </span>
      <RuiButton
        size="sm"
        variant="text"
        color="primary"
        data-testid="bank-balances-connection-action"
        @click="act()"
      >
        {{ t(status.action) }}
      </RuiButton>
    </template>
  </li>
</template>
