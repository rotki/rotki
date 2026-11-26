<script setup lang="ts">
import { RuiButton, RuiIcon, type RuiIcons } from '@rotki/ui-library';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import TableEmptyNotice from '@/modules/core/table/TableEmptyNotice.vue';

const { filtered } = defineProps<{
  filtered: boolean;
}>();

const emit = defineEmits<{
  'clear-filters': [];
  'add': [];
}>();

const { t } = useI18n({ useScope: 'global' });

/** An empty table says whether the filters hid every account or there are none yet, and offers the way out. */
const emptyNotice = computed<{ icon: RuiIcons; title: string; description: string }>(() => filtered
  ? {
      description: t('account_balances.empty.filtered_description'),
      icon: 'lu-search-x',
      title: t('account_balances.empty.filtered_title'),
    }
  : {
      description: t('account_balances.empty.description'),
      icon: 'lu-wallet-minimal',
      title: t('account_balances.empty.title'),
    });
</script>

<template>
  <TableEmptyNotice
    :icon="emptyNotice.icon"
    :title="emptyNotice.title"
    :description="emptyNotice.description"
  >
    <RuiButton
      v-if="filtered"
      variant="outlined"
      color="primary"
      data-testid="accounts-empty-clear-filters"
      @click="emit('clear-filters')"
    >
      {{ t('account_balances.empty.clear_filters') }}
    </RuiButton>
    <RuiButton
      v-else
      color="primary"
      data-testid="accounts-empty-add"
      @click="emit('add')"
    >
      <template #prepend>
        <RuiIcon name="lu-plus" />
      </template>
      {{ t('blockchain_balances.add_account') }}
    </RuiButton>
  </TableEmptyNotice>
</template>
