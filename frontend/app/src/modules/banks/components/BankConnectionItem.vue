<script setup lang="ts">
import type { BankConnection } from '@/modules/banks/types';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import TimeAgoDisplay from '@/modules/shell/components/display/TimeAgoDisplay.vue';

const { connection } = defineProps<{ connection: BankConnection }>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

type ConnectionState = 'authentication' | 'failed' | 'ok';

/** A pending TAN outranks an older failure: answering it is what unblocks the connection. */
const state = computed<ConnectionState>(() => {
  if (connection.syncStatus.authChallenge)
    return 'authentication';
  if (connection.syncStatus.lastError)
    return 'failed';
  return 'ok';
});

async function act(): Promise<void> {
  const query: Record<string, string> = get(state) === 'authentication'
    ? { authenticate: connection.name, location: connection.location }
    : {};
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

    <template v-if="state !== 'ok'">
      <span
        class="flex items-center gap-1 text-caption min-w-0"
        :class="state === 'authentication' ? 'text-rui-warning' : 'text-rui-error'"
        data-testid="bank-balances-connection-status"
      >
        <RuiIcon
          :name="state === 'authentication' ? 'lu-shield-alert' : 'lu-circle-alert'"
          size="14"
          class="shrink-0"
        />
        <span class="truncate">
          {{ state === 'authentication'
            ? t('bank_balances.status.authentication')
            : t('bank_balances.status.failed', { error: connection.syncStatus.lastError }) }}
        </span>
      </span>
      <RuiButton
        size="sm"
        variant="text"
        color="primary"
        data-testid="bank-balances-connection-action"
        @click="act()"
      >
        {{ state === 'authentication' ? t('bank_balances.status.authenticate') : t('bank_balances.status.review') }}
      </RuiButton>
    </template>
  </li>
</template>
