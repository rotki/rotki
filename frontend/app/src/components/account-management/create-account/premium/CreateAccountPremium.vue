<script lang="ts" setup>
import { type Ref } from 'vue';
import { type PremiumSetup } from '@/types/login';
import CreateAccountPremiumForm from '@/components/account-management/create-account/premium/CreateAccountPremiumForm.vue';

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

const { premiumEnabled, form } = toRefs(props);

const { t } = useI18n();

const store = useMainStore();
const { newUser } = toRefs(store);

const valid: Ref<boolean> = ref(false);

const premiumSelectionButtons = [
  { value: false, text: t('common.actions.no') },
  { value: true, text: t('create_account.premium.button_premium_approve') }
];
</script>

<template>
  <div class="space-y-6">
    <i18n
      tag="div"
      path="create_account.premium.premium_question"
      class="text-center text-rui-text-secondary whitespace-break-spaces"
    >
      <template #premiumLink>
        <BaseExternalLink
          :text="t('create_account.premium.premium_link_text')"
          href="https://rotki.com/products"
          class="!text-rui-text-secondary underline"
        />
      </template>
    </i18n>
    <div class="mt-8 flex justify-center gap-5">
      <RuiButton
        v-for="(button, i) in premiumSelectionButtons"
        :key="i"
        rounded
        :variant="button.value === premiumEnabled ? 'filled' : 'outlined'"
        color="primary"
        @click="emit('update:premium-enabled', button.value)"
      >
        <template #prepend>
          <RuiIcon
            class="-ml-2"
            :name="
              button.value === premiumEnabled
                ? 'radio-button-line'
                : 'checkbox-blank-circle-line'
            "
          />
        </template>
        {{ button.text }}
      </RuiButton>
    </div>
    <CreateAccountPremiumForm
      class="mt-8"
      :loading="loading"
      :enabled="premiumEnabled"
      :form="form"
      :valid.sync="valid"
      @update:form="emit('update:form', $event)"
    />
    <div class="grid grid-cols-2 gap-4">
      <RuiButton
        size="lg"
        class="w-full"
        :disabled="loading || newUser"
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
