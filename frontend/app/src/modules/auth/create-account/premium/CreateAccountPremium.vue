<script lang="ts" setup>
import type { CreateAccountMode } from '@/modules/auth/create-account/types';
import type { PremiumSetup } from '@/modules/auth/login';
import { externalLinks } from '@shared/external-links';
import CreateAccountPremiumForm
  from '@/modules/auth/create-account/premium/CreateAccountPremiumForm.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const form = defineModel<PremiumSetup>('form', { required: true });
const premiumEnabled = defineModel<boolean>('premiumEnabled', { required: true });

const { mode } = defineProps<{
  loading: boolean;
  mode: CreateAccountMode;
}>();

const emit = defineEmits<{
  back: [];
  next: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const valid = ref<boolean>(false);

const isRestoreMode = computed<boolean>(() => mode === 'restore');

/** The segmented choice keys on strings, so the boolean model never meets an absent-prop `false`. */
const premiumChoice = computed<'yes' | 'no'>({
  get: () => (get(premiumEnabled) ? 'yes' : 'no'),
  set: (value: 'yes' | 'no') => set(premiumEnabled, value === 'yes'),
});
</script>

<template>
  <div class="space-y-6">
    <!-- one block, so the stack's gap never sits above the collapsing fields, which carry their own -->
    <div>
      <i18n-t
        v-if="isRestoreMode"
        scope="global"
        tag="p"
        keypath="create_account.premium.restore_question"
        class="text-body-1 text-rui-text-secondary"
      >
        <template #premiumLink>
          <ExternalLink
            :text="t('create_account.premium.account_link')"
            :url="externalLinks.manageSubscriptions"
          />
        </template>
      </i18n-t>
      <i18n-t
        v-else
        scope="global"
        tag="p"
        keypath="create_account.premium.premium_question"
        class="text-body-1 text-rui-text-secondary"
      >
        <template #premiumLink>
          <ExternalLink
            :text="t('create_account.premium.get_premium')"
            premium
          />
        </template>
      </i18n-t>
      <RuiButtonGroup
        v-if="!isRestoreMode"
        v-model="premiumChoice"
        class="w-full *:flex-1 mt-6"
        color="primary"
        variant="segmented"
        required
        data-testid="create-account-premium-choice"
      >
        <RuiButton model-value="no">
          {{ t('common.actions.no') }}
        </RuiButton>
        <RuiButton model-value="yes">
          {{ t('create_account.premium.button_premium_approve') }}
        </RuiButton>
      </RuiButtonGroup>
      <CreateAccountPremiumForm
        v-model:valid="valid"
        v-model:form="form"
        :loading="loading"
        :enabled="premiumEnabled"
      />
    </div>
    <div class="grid grid-cols-2 gap-4">
      <RuiButton
        size="lg"
        class="w-full"
        :disabled="loading"
        @click="emit('back')"
      >
        {{ t('common.actions.back') }}
      </RuiButton>
      <RuiButton
        data-testid="create-account-premium-continue"
        size="lg"
        class="w-full"
        :disabled="!valid"
        :loading="loading"
        color="primary"
        @click="emit('next')"
      >
        {{ t('common.actions.continue') }}
      </RuiButton>
    </div>
  </div>
</template>
