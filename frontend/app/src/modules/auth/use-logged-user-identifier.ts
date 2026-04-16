export const useLoggedUserIdentifier = createSharedComposable(() => useSessionStorage<string | undefined>('rotki.logged_user_id', undefined));
