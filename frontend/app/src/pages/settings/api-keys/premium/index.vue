<script setup lang="ts">
import { type Ref } from 'vue';
import { required } from '@vuelidate/validators';
import useVuelidate from '@vuelidate/core';
import { toMessages } from '@/utils/validation';

const { username } = storeToRefs(useSessionAuthStore());
const { update } = useSettingsStore();
const store = usePremiumStore();
const { premium, premiumSync } = storeToRefs(store);
const { setup, deletePremium } = store;

const { t } = useI18n();

const { premiumUserLoggedIn } = useInterop();

const apiKey: Ref<string> = ref('');
const apiSecret: Ref<string> = ref('');
const sync: Ref<boolean> = ref(false);
const edit: Ref<boolean> = ref(true);
const $externalResults: Ref<Record<string, string[]>> = ref({});

const mainActionText = computed(() => {
  if (!get(premium)) {
    return t('premium_settings.actions.setup');
  } else if (!get(edit)) {
    return t('premium_settings.actions.replace');
  }
  return t('common.actions.save');
});

const rules = {
  apiKey: { required },
  apiSecret: { required }
};

const v$ = useVuelidate(
  rules,
  {
    apiKey,
    apiSecret
  },
  { $autoDirty: true, $externalResults }
);

const onSyncChange = async () => {
  await update({ premiumShouldSync: get(sync) });
};

const cancelEdit = async () => {
  set(edit, false);
  set(apiKey, '');
  set(apiSecret, '');
  get(v$).$reset();
};

const reset = () => {
  set(apiSecret, '');
  set(apiKey, '');
  set(edit, false);
  get(v$).$reset();
};

const setupPremium = async () => {
  if (get(premium) && !get(edit)) {
    set(edit, true);
    return;
  }

  set($externalResults, {});
  if (!(await get(v$).$validate())) {
    return;
  }

  const result = await setup({
    username: get(username),
    apiKey: get(apiKey),
    apiSecret: get(apiSecret)
  });

  if (!result.success) {
    if (typeof result.message === 'string') {
      set($externalResults, {
        ...get($externalResults),
        apiKey: [result.message ?? t('premium_settings.error.setting_failed')]
      });
    } else {
      set($externalResults, result.message);
    }

    return;
  }
  premiumUserLoggedIn(true);
  reset();
};

const remove = async () => {
  if (!get(premium)) {
    return;
  }
  const result = await deletePremium();
  if (!result.success) {
    set($externalResults, {
      ...get($externalResults),
      apiKey: [result.message ?? t('premium_settings.error.removing_failed')]
    });
    return;
  }
  premiumUserLoggedIn(false);
  reset();
};

onMounted(() => {
  set(sync, get(premiumSync));
  set(edit, !get(premium) && !get(edit));
});

const { show } = useConfirmStore();

const showDeleteConfirmation = () => {
  show(
    {
      title: t('premium_settings.delete_confirmation.title'),
      message: t('premium_settings.delete_confirmation.message'),
      primaryAction: t('common.actions.delete'),
      secondaryAction: t('common.actions.cancel')
    },
    remove
  );
};

const css = useCssModule();
</script>

<template>
  <TablePageLayout
    :title="[
      t('navigation_menu.api_keys'),
      t('navigation_menu.api_keys_sub.premium')
    ]"
  >
    <RuiCard>
      <div class="flex flex-col gap-2">
        <div class="flex flex-row-reverse">
          <HintMenuIcon>
            <i18n tag="div" path="premium_settings.subtitle">
              <ExternalLink :text="t('premium_settings.title')" premium />
            </i18n>
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

      <div v-if="premium" class="flex flex-row gap-2">
        <RuiIcon name="checkbox-circle-line" color="success" />
        {{ t('premium_settings.premium_active') }}
      </div>

      <VSwitch
        v-model="sync"
        :disabled="!premium || edit"
        hide-details
        :label="t('premium_settings.actions.sync')"
        @change="onSyncChange()"
      />

      <template #footer>
        <div class="flex flex-row gap-2 pa-3" :class="css.buttons">
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
  </TablePageLayout>
</template>

<style lang="scss" module>
.buttons {
  > button {
    @apply min-w-[7rem];
  }
}
</style>
