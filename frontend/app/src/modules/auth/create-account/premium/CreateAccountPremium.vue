<script lang="ts" setup>
import type { PremiumSetup } from '@/modules/auth/login';
import { externalLinks } from '@shared/external-links';
import CreateAccountStepActions from '@/modules/auth/create-account/CreateAccountStepActions.vue';
import CreateAccountPremiumForm
  from '@/modules/auth/create-account/premium/CreateAccountPremiumForm.vue';
import { useStepCheck } from '@/modules/auth/create-account/use-step-check';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const form = defineModel<PremiumSetup>('form', { required: true });

defineProps<{
  loading: boolean;
}>();

const emit = defineEmits<{
  back: [];
  next: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const premium = useTemplateRef<InstanceType<typeof CreateAccountPremiumForm>>('premium');

const { issueCount, validate } = useStepCheck(premium);

async function next(): Promise<void> {
  if (await validate())
    emit('next');
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <i18n-t
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
    <CreateAccountPremiumForm
      ref="premium"
      v-model="form"
      :loading="loading"
    />
    <CreateAccountStepActions
      :next-label="t('common.actions.continue')"
      next-test-id="create-account-premium-continue"
      :issue-count="issueCount"
      :loading="loading"
      @back="emit('back')"
      @next="next()"
    />
  </div>
</template>
