<script setup lang="ts">
import type { EnhancedProviderDetail } from '@/modules/onchain/wallet-providers/provider-detection';

interface Props {
  providers: EnhancedProviderDetail[];
  loading?: boolean;
}

interface Emits {
  'select-provider': [provider: EnhancedProviderDetail];
}

const modelValue = defineModel<boolean>({ default: false });

withDefaults(defineProps<Props>(), {
  loading: false,
});

const emit = defineEmits<Emits>();

const { t } = useI18n({ useScope: 'global' });

function selectProvider(provider: EnhancedProviderDetail): void {
  emit('select-provider', provider);
  set(modelValue, false);
}

function handleCancel(): void {
  set(modelValue, false);
}
</script>

<template>
  <RuiDialog
    v-model="modelValue"
    max-width="500"
    :persistent="true"
  >
    <RuiCard>
      <template #header>
        <div class="flex items-center justify-between">
          <div class="text-h6">
            {{ t('wallet_provider_selection.title') }}
          </div>
          <RuiButton
            v-if="!loading"
            variant="text"
            icon
            @click="handleCancel()"
          >
            <RuiIcon name="lu-x" />
          </RuiButton>
        </div>
      </template>

      <div class="pb-2">
        <div class="text-body-1 text-rui-text-secondary mb-6">
          {{ t('wallet_provider_selection.description') }}
        </div>

        <div
          v-if="loading"
          class="grid grid-cols-2 gap-4"
        >
          <RuiSkeletonLoader
            v-for="i in 4"
            :key="i"
            class="h-24"
          />
        </div>

        <div
          v-else-if="providers.length > 0"
          class="grid grid-cols-2 gap-4"
        >
          <RuiButton
            v-for="provider in providers"
            :key="provider.info.uuid"
            variant="outlined"
            color="primary"
            class="flex-col text-center p-4 h-24 hover:bg-rui-grey-50 dark:hover:bg-rui-grey-800"
            @click="selectProvider(provider)"
          >
            <img
              :src="provider.info.icon"
              :alt="provider.info.name"
              class="w-8 h-8 mx-auto mb-2"
            />
            <div class="text-sm font-medium">
              {{ provider.info.name }}
            </div>
          </RuiButton>
        </div>

        <div
          v-else
          class="text-center py-8"
        >
          <RuiIcon
            name="wallet-line"
            size="48"
            class="text-rui-text-secondary mb-4"
          />
          <div class="text-h6 mb-2">
            {{ t('wallet_provider_selection.no_providers.title') }}
          </div>
          <div class="text-body-2 text-rui-text-secondary mb-6">
            {{ t('wallet_provider_selection.no_providers.description') }}
          </div>
          <RuiButton
            color="primary"
            @click="handleCancel()"
          >
            {{ t('common.actions.close') }}
          </RuiButton>
        </div>
      </div>

      <template
        v-if="providers.length > 0 && !loading"
        #footer
      >
        <div class="flex justify-end gap-2">
          <RuiButton
            variant="outlined"
            @click="handleCancel()"
          >
            {{ t('common.actions.cancel') }}
          </RuiButton>
        </div>
      </template>
    </RuiCard>
  </RuiDialog>
</template>
