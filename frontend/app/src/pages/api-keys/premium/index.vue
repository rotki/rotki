<script setup lang="ts">
import { externalLinks } from '@shared/external-links';
import useVuelidate from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import HintMenuIcon from '@/components/HintMenuIcon.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import AutomaticSyncSetting from '@/components/status/sync/AutomaticSyncSetting.vue';
import { useInterop } from '@/composables/electron-interop';
import { usePremiumHelper } from '@/composables/premium';
import { toMessages } from '@/modules/common/validation/validation';
import PremiumDeviceList from '@/modules/premium/devices/components/PremiumDeviceList.vue';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { usePremiumOperations } from '@/modules/premium/use-premium-operations';
import { useConfirmStore } from '@/store/confirm';
import { useMessageStore } from '@/store/message';
import { useSessionAuthStore } from '@/store/session/auth';
import { usePremiumStore } from '@/store/session/premium';

defineOptions({
  name: 'PremiumApiKeys',
});

const { t } = useI18n({ useScope: 'global' });

const apiKey = ref<string>('');
const apiSecret = ref<string>('');
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

const rules = {
  apiKey: { required },
  apiSecret: { required },
};

const v$ = useVuelidate(
  rules,
  {
    apiKey,
    apiSecret,
  },
  { $autoDirty: true },
);

function cancelEdit() {
  set(edit, false);
  set(apiKey, '');
  set(apiSecret, '');
  get(v$).$reset();
}

function reset() {
  set(apiSecret, '');
  set(apiKey, '');
  set(edit, false);
  get(v$).$reset();
}

async function setupPremium() {
  if (get(premium) && !get(edit)) {
    set(edit, true);
    return;
  }

  set(error, undefined);
  if (!(await get(v$).$validate()))
    return;

  const result = await setup({
    apiKey: get(apiKey),
    apiSecret: get(apiSecret),
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
          v-model.trim="apiKey"
          data-cy="premium__api-key"
          variant="outlined"
          color="primary"
          :disabled="premium && !edit"
          :error-messages="toMessages(v$.apiKey)"
          :label="t('premium_settings.fields.api_key')"
          @blur="v$.$touch()"
        />

        <RuiRevealableTextField
          v-model.trim="apiSecret"
          data-cy="premium__api-secret"
          variant="outlined"
          color="primary"
          :disabled="premium && !edit"
          :error-messages="toMessages(v$.apiSecret)"
          :label="t('premium_settings.fields.api_secret')"
          @blur="v$.$touch()"
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
        <div class="flex flex-row gap-2">
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
              data-cy="premium__delete"
              @click="showDeleteConfirmation()"
            >
              {{ t('premium_settings.actions.delete') }}
            </RuiButton>
          </template>

          <RuiButton
            class="min-w-28"
            color="primary"
            type="submit"
            data-cy="premium__setup"
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
