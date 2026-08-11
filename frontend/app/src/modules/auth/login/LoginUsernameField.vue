<script setup lang="ts">
import { focusInput } from '@/modules/auth/login/focus-input';
import LoginNoProfilesMessage from '@/modules/auth/login/LoginNoProfilesMessage.vue';
import { sortUsernamesByKeyword } from '@/modules/auth/login/sort-usernames';
import { useSavedProfiles } from '@/modules/auth/use-saved-profiles';

const username = defineModel<string>({ required: true });
const search = defineModel<string>('search', { required: true });

const {
  disabled,
  errorMessages = [],
  isDocker,
  loading,
} = defineProps<{
  disabled: boolean;
  loading: boolean;
  isDocker?: boolean;
  errorMessages?: string[];
}>();

const emit = defineEmits<{
  'new-account': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const isTest = import.meta.env.VITE_TEST;

const inputRef = useTemplateRef('inputRef');

const { loadProfiles, savedUsernames } = useSavedProfiles();

// A plain text field is used on docker (where profiles are not enumerable) and under test,
// where the autocomplete's overlay makes the input awkward to drive.
const usePlainField = computed<boolean>(() => !!isDocker || !!isTest);

const orderedUsernames = computed<string[]>(() => sortUsernamesByKeyword(get(savedUsernames), get(search)));

function focus(): void {
  focusInput(get(inputRef));
}

defineExpose({ focus });
</script>

<template>
  <RuiTextField
    v-if="usePlainField"
    ref="inputRef"
    v-model="username"
    variant="outlined"
    color="primary"
    autocomplete="username"
    :label="t('login.label_username')"
    :error-messages="errorMessages"
    :disabled="disabled"
    class="mb-2"
    data-testid="username-input"
    dense
  />
  <RuiAutoComplete
    v-else
    ref="inputRef"
    v-model="username"
    v-model:search-input="search"
    :label="t('login.label_username')"
    :options="orderedUsernames"
    :disabled="disabled"
    :error-messages="errorMessages"
    data-testid="username-input"
    class="mb-2 [&_[data-id=activator]]:bg-transparent"
    auto-select-first
    :hide-no-data="savedUsernames.length > 0"
    clearable
    variant="outlined"
    :item-height="38"
    dense
  >
    <template #item="{ item }">
      <div class="py-1">
        {{ item }}
      </div>
    </template>
    <template #no-data>
      <LoginNoProfilesMessage
        :loading="loading"
        @refresh-profiles="loadProfiles()"
        @new-account="emit('new-account')"
      />
    </template>
  </RuiAutoComplete>
</template>
