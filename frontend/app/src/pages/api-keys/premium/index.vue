<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import { msg } from '@/message-key';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { useForm } from '@/modules/core/form/use-form';
import PremiumDeviceList from '@/modules/premium/devices/components/PremiumDeviceList.vue';
import {
  emptyPremiumCredentialsForm,
  type PremiumCredentialsFormState,
  premiumCredentialsSchema,
} from '@/modules/premium/premium-credentials-form';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { usePremiumHelper } from '@/modules/premium/use-premium-helper';
import { usePremiumOperations } from '@/modules/premium/use-premium-operations';
import { usePremiumStore } from '@/modules/premium/use-premium-store';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import ExternalLink from '@/modules/shell/components/ExternalLink.vue';
import HintMenuIcon from '@/modules/shell/components/HintMenuIcon.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import AutomaticSyncSetting from '@/modules/shell/sync-progress/AutomaticSyncSetting.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.api_keys_sub.premium'), icon: 'lu-crown', parent: '/api-keys/', order: 10, drawer: 'api-keys-premium' },
  },
});

defineOptions({
  name: 'PremiumApiKeys',
});

const { t } = useI18n({ useScope: 'global' });

const edit = ref<boolean>(true);
const error = ref<string>();

const { username } = storeToRefs(useSessionAuthStore());
const { premium } = storeToRefs(usePremiumStore());
const { deletePremium, setup } = usePremiumOperations();
const { show } = useConfirmStore();
const { setMessage } = useMessageStore();

const { currentTier } = usePremiumHelper();
const { openUrl, premiumUserLoggedIn } = useInterop();
const { allowed: cloudBackupAllowed } = useFeatureAccess(PremiumFeature.CLOUD_BACKUP);

const mainActionText = computed<string>(() => {
  if (!get(premium))
    return t('premium_settings.actions.setup');
  else if (!get(edit))
    return t('premium_settings.actions.replace');

  return t('common.actions.save');
});

const form = useForm<PremiumCredentialsFormState, PremiumCredentialsFormState>({
  initial: emptyPremiumCredentialsForm,
  schema: premiumCredentialsSchema(),
  // The page decides what to do with the outcome, so the persist stays in `setupPremium`.
  submit: async (): Promise<{ success: boolean }> => Promise.resolve({ success: true }),
  transform: (state): PremiumCredentialsFormState => ({ ...state }),
});

function cancelEdit(): void {
  set(edit, false);
  form.reset();
}

function reset(): void {
  set(edit, false);
  form.reset();
}

async function setupPremium(): Promise<void> {
  if (get(premium) && !get(edit)) {
    set(edit, true);
    return;
  }

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

async function remove() {
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

function showDeleteConfirmation() {
  show(
    {
      message: t('premium_settings.delete_confirmation.message'),
      primaryAction: t('common.actions.delete'),
      secondaryAction: t('common.actions.cancel'),
      title: t('premium_settings.delete_confirmation.title'),
    },
    remove,
  );
}

watch(error, (errorMessage) => {
  if (!errorMessage)
    return;

  const DEVICE_LIMIT_PLACEHOLDER = '_DEVICE_LIMIT_LINK_';

  if (errorMessage.includes(DEVICE_LIMIT_PLACEHOLDER)) {
    const cleanedMessage = errorMessage.replace(DEVICE_LIMIT_PLACEHOLDER, '').trim();

    show(
      {
        message: cleanedMessage,
        primaryAction: t('premium_settings.error.device_limit.learn_more'),
        secondaryAction: t('common.actions.dismiss'),
        title: t('premium_settings.error.setting_failed'),
        type: 'warning',
      },
      async () => {
        await openUrl(externalLinks.premiumDevices);
      },
    );
  }
  else {
    setMessage({
      description: t('premium_settings.error.setup_failed_description', { error: errorMessage }),
      success: false,
      title: t('premium_settings.error.setting_failed'),
    });
  }
});

onMounted(() => {
  set(edit, !get(premium) && !get(edit));
});
</script>

<template>
  <TablePageLayout
    :title="[
      t('navigation_menu.api_keys'),
      t('navigation_menu.api_keys_sub.premium'),
    ]"
  >
    <RuiCard>
      <div class="flex flex-col gap-2">
        <div class="flex flex-row-reverse">
          <HintMenuIcon>
            <i18n-t
              scope="global"
              tag="div"
              keypath="premium_settings.subtitle"
            >
              <ExternalLink
                color="primary"
                :text="t('premium_settings.title')"
                premium
              />
            </i18n-t>
          </HintMenuIcon>
        </div>

        <RuiRevealableTextField
          v-model.trim="form.state.apiKey"
          data-testid="premium-api-key"
          variant="outlined"
          color="primary"
          :disabled="premium && !edit"
          :error-messages="form.errors('apiKey')"
          :label="t('premium_settings.fields.api_key')"
          @blur="form.touch('apiKey')"
        />

        <RuiRevealableTextField
          v-model.trim="form.state.apiSecret"
          data-testid="premium-api-secret"
          variant="outlined"
          color="primary"
          :disabled="premium && !edit"
          :error-messages="form.errors('apiSecret')"
          :label="t('premium_settings.fields.api_secret')"
          @blur="form.touch('apiSecret')"
        />
      </div>

      <RuiAlert
        v-if="premium"
        type="success"
      >
        {{ t('premium_settings.premium_active') }}
      </RuiAlert>

      <div
        v-if="premium"
        class="flex items-center justify-between mt-4 px-2"
      >
        <div class="flex items-center gap-3">
          <span class="text-rui-text-secondary text-body-2">
            {{ t('premium_settings.current_plan_label') }} <span class="font-bold text-rui-text">{{ currentTier || '—' }}</span>
          </span>
        </div>
        <ExternalLink
          :url="externalLinks.manageSubscriptions"
          :text="t('premium_settings.manage_or_upgrade')"
          color="primary"
        />
      </div>

      <AutomaticSyncSetting
        class="mt-6"
        :disabled="!premium || edit || !cloudBackupAllowed"
      />

      <RuiAlert
        v-if="premium && !cloudBackupAllowed"
        type="info"
        class="mt-4"
      >
        <i18n-t
          scope="global"
          tag="span"
          keypath="premium_settings.cloud_backup_unavailable"
        >
          <template #link>
            <ExternalLink
              :url="externalLinks.manageSubscriptions"
              :text="t('premium_settings.cloud_backup_upgrade_link')"
              color="primary"
            />
          </template>
        </i18n-t>
      </RuiAlert>

      <template #footer>
        <div class="flex gap-2">
          <template v-if="premium">
            <RuiButton
              v-if="edit"
              class="min-w-28"
              color="primary"
              variant="outlined"
              @click="cancelEdit()"
            >
              {{ t('common.actions.cancel') }}
            </RuiButton>

            <RuiButton
              v-else
              class="min-w-28"
              variant="outlined"
              color="primary"
              type="submit"
              data-testid="premium-delete"
              @click="showDeleteConfirmation()"
            >
              {{ t('premium_settings.actions.delete') }}
            </RuiButton>
          </template>

          <RuiButton
            class="min-w-28"
            color="primary"
            type="submit"
            data-testid="premium-setup"
            @click="setupPremium()"
          >
            {{ mainActionText }}
          </RuiButton>
        </div>
      </template>
    </RuiCard>
    <PremiumDeviceList v-if="premium" />
  </TablePageLayout>
</template>
