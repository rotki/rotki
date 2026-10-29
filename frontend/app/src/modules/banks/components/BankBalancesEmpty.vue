<script setup lang="ts">
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import TableEmptyNotice from '@/modules/core/table/TableEmptyNotice.vue';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';

const emit = defineEmits<{ connect: [connector?: string] }>();

const { t } = useI18n({ useScope: 'global' });
const { manifests } = storeToRefs(useBankConnectionsStore());
</script>

<template>
  <div
    class="rounded-rui-card border border-rui-divider bg-rui-surface pb-10"
    data-testid="bank-balances-empty"
  >
    <TableEmptyNotice
      icon="lu-landmark"
      :title="t('bank_balances.empty.title')"
      :description="t('bank_balances.empty.description')"
    >
      <RuiButton
        color="primary"
        data-testid="bank-balances-empty-connect"
        @click="emit('connect')"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('bank_balances.add_bank') }}
      </RuiButton>
    </TableEmptyNotice>

    <div
      v-if="manifests.length > 0"
      class="flex flex-col items-center gap-3 px-4"
    >
      <span class="text-caption uppercase tracking-wide text-rui-text-secondary">
        {{ t('bank_balances.empty.supported') }}
      </span>
      <div class="flex flex-wrap justify-center gap-2">
        <RuiButton
          v-for="manifest in manifests"
          :key="manifest.connectorIdentifier"
          variant="outlined"
          data-testid="bank-balances-empty-shortcut"
          :data-bank="manifest.connectorIdentifier"
          @click="emit('connect', manifest.connectorIdentifier)"
        >
          <template #prepend>
            <LocationIcon
              :item="manifest.fixedLocation ?? 'banks'"
              icon
              size="18px"
            />
          </template>
          {{ manifest.displayName }}
        </RuiButton>
      </div>
    </div>
  </div>
</template>
