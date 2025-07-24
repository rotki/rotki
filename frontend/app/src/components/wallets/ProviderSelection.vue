<script setup lang="ts">
import type { EIP6963ProviderDetail } from '@/types';

interface Props {
  providers: EIP6963ProviderDetail[];
  loading?: boolean;
  variant?: 'grid' | 'list';
  showTitle?: boolean;
}

interface Emits {
  'select-provider': [provider: EIP6963ProviderDetail];
}

withDefaults(defineProps<Props>(), {
  loading: false,
  showTitle: true,
  variant: 'grid',
});

const emit = defineEmits<Emits>();

const { t } = useI18n({ useScope: 'global' });

function selectProvider(provider: EIP6963ProviderDetail): void {
  emit('select-provider', provider);
}
</script>

<template>
  <div>
    <div
      v-if="showTitle"
      class="text-h6 mb-4"
    >
      {{ t('wallet_provider_selection.choose_wallet') }}
    </div>

    <div
      v-if="loading"
      :class="variant === 'grid' ? 'grid grid-cols-2 gap-3' : 'space-y-2'"
    >
      <RuiSkeletonLoader
        v-for="i in 4"
        :key="i"
        :class="variant === 'grid' ? 'h-20' : 'h-12'"
      />
    </div>

    <div
      v-else-if="providers.length > 0"
      :class="variant === 'grid' ? 'grid grid-cols-2 gap-3' : 'space-y-2'"
    >
      <RuiButton
        v-for="provider in providers"
        :key="provider.info.uuid"
        variant="outlined"
        color="primary"
        :class="variant === 'grid'
          ? 'flex-col text-center p-3 h-20 hover:bg-rui-grey-50 dark:hover:bg-rui-grey-800'
          : 'flex items-center justify-start p-3 h-12 hover:bg-rui-grey-50 dark:hover:bg-rui-grey-800'"
        @click="selectProvider(provider)"
      >
        <img
          :src="provider.info.icon"
          :alt="provider.info.name"
          :class="variant === 'grid' ? 'w-6 h-6 mx-auto mb-1' : 'w-6 h-6 mr-3'"
        />
        <div class="text-sm font-medium">
          {{ provider.info.name }}
        </div>
      </RuiButton>
    </div>

    <div
      v-else
      class="text-center py-6"
    >
      <RuiIcon
        name="wallet-line"
        size="32"
        class="text-rui-text-secondary mb-3"
      />
      <div class="text-body-2 text-rui-text-secondary">
        {{ t('wallet_provider_selection.no_providers.description') }}
      </div>
    </div>
  </div>
</template>
