<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import HintMenuIcon from '@/components/HintMenuIcon.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import PremiumDeviceList from '@/components/premium/PremiumDeviceList.vue';
import { useInterop } from '@/composables/electron-interop';
import { useConfirmStore } from '@/store/confirm';
import { useSessionAuthStore } from '@/store/session/auth';
import { usePremiumStore } from '@/store/session/premium';
import { useSettingsStore } from '@/store/settings';
import { toMessages } from '@/utils/validation';

const { username } = storeToRefs(useSessionAuthStore());
const { update } = useSettingsStore();
const store = usePremiumStore();
const { premium, premiumSync } = storeToRefs(store);
const { deletePremium, setup } = store;

const { t } = useI18n({ useScope: 'global' });

const { premiumUserLoggedIn } = useInterop();

const apiKey = ref<string>('');
const apiSecret = ref<string>('');
const sync = ref<boolean>(false);
const edit = ref<boolean>(true);
const $externalResults = ref<Record<string, string[]>>({});

const mainActionText = computed(() => {
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
  { $autoDirty: true, $externalResults },
);

async function onSyncChange() {
  await update({ premiumShouldSync: get(sync) });
}

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

  set($externalResults, {});
  if (!(await get(v$).$validate()))
    return;

  const result = await setup({
    apiKey: get(apiKey),
    apiSecret: get(apiSecret),
    username: get(username),
  });

  if (!result.success) {
    if (typeof result.message === 'string') {
      set($externalResults, {
        ...get($externalResults),
        apiKey: [result.message ?? t('premium_settings.error.setting_failed')],
      });
    }
    else {
      set($externalResults, result.message);
    }

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
    set($externalResults, {
      ...get($externalResults),
      apiKey: [result.message ?? t('premium_settings.error.removing_failed')],
    });
    return;
  }
  premiumUserLoggedIn(false);
  reset();
}

onMounted(() => {
  set(sync, get(premiumSync));
  set(edit, !get(premium) && !get(edit));
});

const { show } = useConfirmStore();

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

      <RuiSwitch
        v-model="sync"
        class="mt-6"
        color="primary"
        :disabled="!premium || edit"
        hide-details
        :label="t('premium_settings.actions.sync')"
        @update:model-value="onSyncChange()"
      />

      <template #footer>
        <div
          class="flex flex-row gap-2 pt-4"
          :class="$style.buttons"
        >
          <template v-if="premium">
            <RuiButton
              v-if="edit"
              color="primary"
              variant="outlined"
              @click="cancelEdit()"
            >
              {{ t('common.actions.cancel') }}
            </RuiButton>

            <RuiButton
              v-else
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

<style lang="scss" module>
.buttons {
  > button {
    @apply min-w-[7rem];
  }
}
</style>
