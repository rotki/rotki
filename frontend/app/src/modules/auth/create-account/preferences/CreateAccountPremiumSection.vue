<script lang="ts" setup>
import type { PremiumSetup } from '@/modules/auth/login';
import { externalLinks } from '@shared/external-links';
import CreateAccountPremiumForm
  from '@/modules/auth/create-account/premium/CreateAccountPremiumForm.vue';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';

const expanded = defineModel<boolean>('expanded', { required: true });
const form = defineModel<PremiumSetup>('form', { required: true });
const shouldSync = defineModel<boolean>('shouldSync', { required: true });

defineProps<{
  loading: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const premium = useTemplateRef<InstanceType<typeof CreateAccountPremiumForm>>('premium');

const errorCount = computed<number>(() => get(premium)?.errorCount ?? 0);

/** A closed section renders no form, and whatever was typed in it is not sent, so it passes. */
async function validate(): Promise<boolean> {
  return await get(premium)?.validate() ?? true;
}

defineExpose({ errorCount, validate });
</script>

<template>
  <div class="rounded-md border border-rui-grey-300 dark:border-rui-grey-800 bg-white dark:bg-transparent">
    <button
      type="button"
      class="flex w-full items-center justify-between gap-3 p-4 text-left font-medium"
      data-testid="create-account-premium-toggle"
      :aria-expanded="expanded"
      :disabled="loading"
      @click="expanded = !expanded"
    >
      <span>{{ t('create_account.premium.toggle') }}</span>
      <RuiIcon
        size="18"
        class="text-rui-primary transition-transform"
        :class="{ 'rotate-180': expanded }"
        name="lu-chevron-down"
      />
    </button>
    <div
      v-if="expanded"
      class="flex flex-col gap-3 px-4 pb-4"
      data-testid="create-account-premium-section"
    >
      <i18n-t
        scope="global"
        tag="p"
        keypath="create_account.premium.where_to_find"
        class="text-body-2 text-rui-text-secondary"
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
        optional
      />
      <RuiCheckbox
        v-model="shouldSync"
        :disabled="loading"
        color="primary"
        details="hidden"
        data-testid="create-account-premium-should-sync"
      >
        <span class="flex flex-col">
          <span>{{ t('create_account.premium.should_sync') }}</span>
          <span class="text-rui-text-secondary">{{ t('create_account.premium.should_sync_hint') }}</span>
        </span>
      </RuiCheckbox>
    </div>
  </div>
</template>
