<script setup lang="ts">
const { loading } = defineProps<{
  loading: boolean;
}>();

const emit = defineEmits<{
  'refresh-profiles': [];
  'new-account': [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex flex-col items-center py-3">
    <div>{{ t('login.no_profiles_found') }}</div>
    <div class="flex items-center gap-1">
      <i18n-t
        scope="global"
        keypath="login.no_profiles_found_action"
      >
        <template #refresh_profiles>
          <RuiButton
            color="primary"
            variant="text"
            class="text-[1em] py-0 px-1"
            :disabled="loading"
            type="button"
            @click="emit('refresh-profiles')"
          >
            <template #prepend>
              <RuiIcon
                name="lu-refresh-ccw"
                size="14"
              />
            </template>
            {{ t('login.button_refresh_profiles') }}
          </RuiButton>
        </template>
        <template #create_account>
          <RuiButton
            color="primary"
            variant="text"
            class="text-[1em] py-0 px-1"
            :disabled="loading"
            type="button"
            @click="emit('new-account')"
          >
            <template #prepend>
              <RuiIcon
                name="lu-plus"
                size="14"
              />
            </template>
            {{ t('login.button_create_account') }}
          </RuiButton>
        </template>
      </i18n-t>
    </div>
  </div>
</template>
