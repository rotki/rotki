<script setup lang="ts">
import HashLink from '@/modules/common/links/HashLink.vue';
import { GnosisPayError, type GnosisPayErrorContext } from '../types';

interface Props {
  validatingAddress: boolean;
  isAddressValid: boolean;
  controlledSafeAddresses: string[];
  validationErrorMessage: string;
  errorType: GnosisPayError | null;
  errorContext: GnosisPayErrorContext;
  errorCloseable: boolean;
}

defineProps<Props>();

const emit = defineEmits<{
  'clear-error': [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="space-y-4">
    <!-- Validating address -->
    <RuiAlert
      v-if="validatingAddress"
      type="info"
    >
      {{ t('external_services.gnosispay.siwe.validating_address') }}
    </RuiAlert>

    <!-- Address validation success -->
    <RuiAlert
      v-else-if="isAddressValid"
      type="success"
    >
      <div>{{ t('external_services.gnosispay.siwe.controlled_safe') }}</div>
      <div class="mt-2 font-mono text-caption">
        <div
          v-for="safeAddress in controlledSafeAddresses"
          :key="safeAddress"
        >
          <HashLink
            :truncate-length="0"
            :text="safeAddress"
            location="gnosis"
          />
        </div>
      </div>
    </RuiAlert>

    <!-- Validation errors -->
    <RuiAlert
      v-if="validationErrorMessage"
      :type="errorType === GnosisPayError.INVALID_ADDRESS ? 'warning' : 'error'"
      variant="default"
      :closeable="errorCloseable"
      @close="emit('clear-error')"
    >
      <div class="whitespace-pre-line">
        {{ validationErrorMessage }}
      </div>
    </RuiAlert>

    <!-- Invalid address - show allowed admin addresses -->
    <div v-if="errorType === GnosisPayError.INVALID_ADDRESS">
      <div class="text-caption text-rui-text-secondary mb-2">
        {{ t('external_services.gnosispay.errors.allowed_admin_addresses') }}
      </div>
      <template v-if="errorContext?.adminsMapping">
        <div
          v-for="[safeAddress, adminAddresses] in Object.entries(errorContext.adminsMapping)"
          :key="safeAddress"
          class="mb-3"
        >
          <div class="mb-1 text-rui-text-secondary flex gap-2 items-center">
            <div class="text-[10px] uppercase">
              {{ t('external_services.gnosispay.errors.safe_wallet') }}
            </div>
            <HashLink
              :truncate-length="0"
              :text="safeAddress"
              location="gnosis"
            />
          </div>
          <div class="relative ml-[5.25rem]">
            <div class="absolute border-l border-default flex h-[calc(100%-0.75rem)]" />
            <div
              v-for="adminAddress in adminAddresses"
              :key="adminAddress"
              class="font-medium flex items-center gap-2"
            >
              <div class="border-t w-2 border-default" />
              <HashLink
                :truncate-length="0"
                :text="adminAddress"
                location="gnosis"
              />
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>
