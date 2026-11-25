import { createSharedComposable, useSessionStorage } from '@vueuse/core';

export const useLoggedUserIdentifier = createSharedComposable(() => useSessionStorage<string | undefined>('rotki.logged_user_id', undefined));
