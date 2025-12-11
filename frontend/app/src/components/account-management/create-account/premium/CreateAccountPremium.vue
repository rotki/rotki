<script lang="ts" setup>
import type { PremiumSetup } from '@/types/login';
import CreateAccountPremiumForm
  from '@/components/account-management/create-account/premium/CreateAccountPremiumForm.vue';
import ExternalLink from '@/components/helper/ExternalLink.vue';

const form = defineModel<PremiumSetup>('form', { required: true });
const premiumEnabled = defineModel<boolean>('premiumEnabled', { required: true });

defineProps<{
  loading: boolean;
}>();

const emit = defineEmits<{
  back: [];
  next: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const valid = ref<boolean>(false);

const premiumSelectionButtons = computed(() => [
  { text: t('common.actions.no'), value: false },
  { text: t('create_account.premium.button_premium_approve'), value: true },
]);
</script>

<template>
  <div class="space-y-6">
    <i18n-t
      scope="global"
      tag="div"
      keypath="create_account.premium.premium_question"
      class="text-center text-rui-text-secondary whitespace-break-spaces"
    >
      <template #premiumLink>
        <ExternalLink
          :text="t('common.here')"
          premium
        />.
      </template>
    </i18n-t>
    <div class="mt-8 flex justify-center gap-5">
      <RuiButton
        v-for="(button, i) in premiumSelectionButtons"
        :key="i"
        rounded
        :variant="button.value === premiumEnabled ? 'default' : 'outlined'"
        color="primary"
        @click="premiumEnabled = button.value"
      >
        <template #prepend>
          <RuiIcon
            class="-ml-2"
            :name="button.value === premiumEnabled ? 'lu-radio-button-fill' : 'lu-checkbox-blank-circle'"
          />
        </template>
        {{ button.text }}
      </RuiButton>
    </div>
    <CreateAccountPremiumForm
      v-model:valid="valid"
      v-model:form="form"
      class="mt-8"
      :loading="loading"
      :enabled="premiumEnabled"
    />
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
        data-cy="create-account__premium__button__continue"
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
