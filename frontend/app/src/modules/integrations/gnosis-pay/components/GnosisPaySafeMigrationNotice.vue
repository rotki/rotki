<script setup lang="ts">
import type { Account } from '@rotki/common';
import AccountDisplay from '@/modules/shell/components/display/AccountDisplay.vue';

const { account, adding = false, keypath } = defineProps<{
  /** The Safe Gnosis Pay moved to or from that rotki does not track yet. */
  account?: Account;
  /** Whether the new or the old Safe is the one missing, which decides the wording. */
  keypath: string;
  adding?: boolean;
}>();

const emit = defineEmits<{
  add: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiAlert
    type="warning"
    :title="t('external_services.gnosispay.safe_migration.title')"
  >
    <div class="flex flex-col items-start gap-2">
      <i18n-t
        v-if="account"
        scope="global"
        tag="div"
        class="text-body-2 break-words"
        :keypath="keypath"
      >
        <template #address>
          <AccountDisplay
            class="inline-flex align-middle max-w-full"
            hide-chain-icon
            :account="account"
          />
        </template>
      </i18n-t>
      <RuiButton
        size="sm"
        color="primary"
        :loading="adding"
        @click="emit('add')"
      >
        <template #prepend>
          <RuiIcon
            name="lu-plus"
            size="16"
          />
        </template>
        {{ t('external_services.gnosispay.safe_migration.add_action') }}
      </RuiButton>
    </div>
  </RuiAlert>
</template>
