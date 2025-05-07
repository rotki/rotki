<script lang="ts" setup>
import type { PremiumSetup } from '@/types/login';
import CreateAccountPremiumForm
  from '@/components/account-management/create-account/premium/CreateAccountPremiumForm.vue';
import ExternalLink from '@/components/helper/ExternalLink.vue';

const props = defineProps<{
  loading: boolean;
  form: PremiumSetup;
  premiumEnabled: boolean;
}>();

const emit = defineEmits<{
  (e: 'back'): void;
  (e: 'next'): void;
  (e: 'update:form', form: PremiumSetup): void;
  (e: 'update:premium-enabled', enabled: boolean): void;
}>();

const { form, premiumEnabled } = toRefs(props);

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
        @click="emit('update:premium-enabled', button.value)"
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
      class="mt-8"
      :loading="loading"
      :enabled="premiumEnabled"
      :form="form"
      @update:form="emit('update:form', $event)"
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
