<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import { msg } from '@/message-key';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { noSubmit, useForm } from '@/modules/core/form/use-form';
import PremiumDeviceList from '@/modules/premium/devices/components/PremiumDeviceList.vue';
import {
  emptyPremiumCredentialsForm,
  type PremiumCredentialsFormState,
  premiumCredentialsSchema,
} from '@/modules/premium/premium-credentials-form';
import PremiumCredentialFields from '@/modules/premium/settings/PremiumCredentialFields.vue';
import PremiumSubscriptionCard from '@/modules/premium/settings/PremiumSubscriptionCard.vue';
import PremiumSyncCard from '@/modules/premium/settings/PremiumSyncCard.vue';
import PremiumUpsellCard from '@/modules/premium/settings/PremiumUpsellCard.vue';
import { usePremiumOperations } from '@/modules/premium/use-premium-operations';
import { usePremiumStore } from '@/modules/premium/use-premium-store';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.api_keys_sub.premium'), icon: 'lu-crown', parent: '/api-keys/', order: 10, drawer: 'api-keys-premium' },
  },
});

defineOptions({
  name: 'PremiumApiKeys',
});

const { t } = useI18n({ useScope: 'global' });

/** Whether an active subscription's key is being replaced; without one the fields always show. */
const replacing = ref<boolean>(false);
const error = ref<string>();

/** Marks a device-limit refusal, whose strip also offers a link to managing the devices. */
const DEVICE_LIMIT_PLACEHOLDER = '_DEVICE_LIMIT_LINK_';

/** Whether the last failure was the device limit, which the strip pairs with a learn-more link. */
const deviceLimitReached = computed<boolean>(() => get(error)?.includes(DEVICE_LIMIT_PLACEHOLDER) ?? false);

/** The last save or remove failure, named above the cards until the next save starts. */
const inlineFailure = computed<string | undefined>(() => get(error)?.replace(DEVICE_LIMIT_PLACEHOLDER, '').trim() || undefined);

const { username } = storeToRefs(useSessionAuthStore());
const { premium } = storeToRefs(usePremiumStore());
const { deletePremium, setup } = usePremiumOperations();
const { openUrl, premiumUserLoggedIn } = useInterop();

const form = useForm<PremiumCredentialsFormState, PremiumCredentialsFormState>({
  initial: emptyPremiumCredentialsForm,
  schema: premiumCredentialsSchema(),
  submit: noSubmit,
  transform: (state): PremiumCredentialsFormState => ({ ...state }),
});

function reset(): void {
  set(replacing, false);
  form.reset();
}

async function saveCredentials(): Promise<void> {
  set(error, undefined);
  if (!form.validate())
    return;

  const result = await setup({
    apiKey: form.state.apiKey,
    apiSecret: form.state.apiSecret,
    username: get(username),
  });

  if (!result.success) {
    set(error, result.message ?? t('premium_settings.error.setting_failed'));
    return;
  }
  premiumUserLoggedIn(true);
  reset();
}

async function remove(): Promise<void> {
  if (!get(premium))
    return;

  const result = await deletePremium();
  if (!result.success) {
    set(error, result.message ?? t('premium_settings.error.removing_failed'));
    return;
  }
  premiumUserLoggedIn(false);
  reset();
}
</script>

<template>
  <TablePageLayout
    :title="[
      t('navigation_menu.api_keys'),
      t('navigation_menu.api_keys_sub.premium'),
    ]"
  >
    <div class="flex flex-col gap-6">
      <FailureStrip
        v-if="inlineFailure"
        :title="t('premium_settings.error.setting_failed')"
        :failure="inlineFailure"
        :retryable="false"
        data-testid="premium-settings-failure"
      >
        <template
          v-if="deviceLimitReached"
          #action
        >
          <button
            type="button"
            class="shrink-0 underline underline-offset-2 hover:no-underline"
            data-testid="premium-settings-device-limit-learn-more"
            @click="openUrl(externalLinks.premiumDevices)"
          >
            {{ t('premium_settings.error.device_limit.learn_more') }}
          </button>
        </template>
      </FailureStrip>
      <PremiumUpsellCard
        v-if="!premium"
        @activate="saveCredentials()"
      >
        <template #credentials>
          <PremiumCredentialFields
            v-model:api-key="form.state.apiKey"
            v-model:api-secret="form.state.apiSecret"
            :api-key-errors="form.errors('apiKey')"
            :api-secret-errors="form.errors('apiSecret')"
            @blur="form.touch($event)"
          />
        </template>
      </PremiumUpsellCard>

      <template v-else>
        <div class="grid lg:grid-cols-3 gap-6">
          <PremiumSubscriptionCard
            class="lg:col-span-2"
            :editing="replacing"
            @replace="replacing = true"
            @cancel="reset()"
            @save="saveCredentials()"
            @remove="remove()"
          >
            <template #credentials>
              <PremiumCredentialFields
                v-model:api-key="form.state.apiKey"
                v-model:api-secret="form.state.apiSecret"
                :api-key-errors="form.errors('apiKey')"
                :api-secret-errors="form.errors('apiSecret')"
                @blur="form.touch($event)"
              />
            </template>
          </PremiumSubscriptionCard>
          <PremiumSyncCard :disabled="replacing" />
        </div>
        <PremiumDeviceList />
      </template>
    </div>
  </TablePageLayout>
</template>
