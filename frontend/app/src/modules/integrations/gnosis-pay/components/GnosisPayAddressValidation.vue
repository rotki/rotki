<script setup lang="ts">
import HashLink from '@/modules/shell/components/HashLink.vue';
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

const showOwners = ref<boolean>(false);
</script>

<template>
  <div class="flex flex-col gap-3">
    <div
      v-if="validatingAddress"
      class="flex items-center gap-2 text-sm text-rui-text-secondary"
    >
      <RuiProgress
        variant="indeterminate"
        circular
        size="16"
        thickness="2"
        color="primary"
      />
      {{ t('external_services.gnosispay.siwe.validating_address') }}
    </div>

    <div
      v-else-if="isAddressValid"
      class="flex flex-col gap-1.5"
      data-testid="gnosis-pay-controlled-safes"
    >
      <div class="flex items-center gap-2 text-sm font-medium text-rui-text">
        <RuiIcon
          name="lu-circle-check"
          size="16"
          class="text-rui-success"
        />
        {{ t('external_services.gnosispay.siwe.controlled_safe') }}
      </div>
      <div
        v-for="safeAddress in controlledSafeAddresses"
        :key="safeAddress"
        class="ml-6 font-mono text-sm"
      >
        <HashLink
          :truncate-length="0"
          :text="safeAddress"
          location="gnosis"
        />
      </div>
    </div>

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

    <div
      v-if="errorType === GnosisPayError.INVALID_ADDRESS && errorContext?.adminsMapping"
      class="flex flex-col items-start gap-2"
    >
      <RuiButton
        variant="text"
        color="primary"
        size="sm"
        data-testid="gnosis-pay-toggle-owners"
        @click="showOwners = !showOwners"
      >
        <template #append>
          <RuiIcon
            :name="showOwners ? 'lu-chevron-up' : 'lu-chevron-down'"
            size="14"
          />
        </template>
        {{ showOwners ? t('external_services.gnosispay.errors.hide_owners') : t('external_services.gnosispay.errors.show_owners') }}
      </RuiButton>
      <template v-if="showOwners">
        <div
          v-for="[safeAddress, adminAddresses] in Object.entries(errorContext.adminsMapping)"
          :key="safeAddress"
          class="mb-1"
        >
          <div class="mb-1 flex items-center gap-2 text-sm text-rui-text-secondary">
            <span class="font-medium">
              {{ t('external_services.gnosispay.errors.safe_wallet') }}
            </span>
            <HashLink
              :truncate-length="0"
              :text="safeAddress"
              location="gnosis"
            />
          </div>
          <div class="ml-2 flex flex-col gap-0.5 border-l border-rui-divider pl-3 text-sm">
            <div
              v-for="adminAddress in adminAddresses"
              :key="adminAddress"
              class="flex items-center gap-2 font-mono"
            >
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
