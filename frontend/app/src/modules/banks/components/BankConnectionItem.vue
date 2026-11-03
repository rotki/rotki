<script setup lang="ts">
import type { BankConnection, BankConnectionIdentity } from '@/modules/banks/types';
import {
  type BankConnectionState,
  bankConnectionState,
  bankConnectionStatus,
  type BankConnectionStatusDisplay,
} from '@/modules/banks/bank-connection-state';
import BankConnectorIcon from '@/modules/banks/components/BankConnectorIcon.vue';
import TimeAgoDisplay from '@/modules/shell/components/display/TimeAgoDisplay.vue';

const { connection } = defineProps<{ connection: BankConnection }>();

const emit = defineEmits<{
  /** syncing again is the way out of an expired TAN; the page that lists the connections runs it */
  sync: [connection: BankConnectionIdentity];
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const state = computed<BankConnectionState>(() => bankConnectionState(connection));

const status = computed<BankConnectionStatusDisplay | undefined>(() => bankConnectionStatus(connection));

/** Only a failure names a reason. */
const statusText = computed<string>(() => {
  const current = get(status);
  if (!current)
    return '';
  return get(state) === 'failed' ? t(current.text, { error: connection.syncStatus.lastError }) : t(current.text);
});

/** A pending TAN opens its answer, an expired one syncs again for a fresh TAN, a failure leads to the connection. */
async function act(): Promise<void> {
  const { connector, name } = connection;
  if (get(state) === 'expired') {
    emit('sync', { connector, name });
    return;
  }
  const query: Record<string, string> = get(state) === 'authentication' ? { authenticate: name, connector } : {};
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
    <BankConnectorIcon :connector="connection.connector" />
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
