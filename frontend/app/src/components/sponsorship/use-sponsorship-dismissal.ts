import type { ComputedRef, Ref } from 'vue';
import { usePremium } from '@/composables/premium';
import { useLoggedUserIdentifier } from '@/composables/user/use-logged-user-identifier';
import { useMainStore } from '@/store/main';
import { isMajorOrMinorUpdate } from '@/utils/version';

interface UseSponsorshipDismissalReturn {
  shouldShowSponsorship: ComputedRef<boolean>;
  canDismissSponsorship: Ref<boolean>;
  dismissSponsorship: () => void;
}

export function useSponsorshipDismissal(): UseSponsorshipDismissalReturn {
  const premium = usePremium();
  const loggedUserId = useLoggedUserIdentifier();
  const { appVersion } = storeToRefs(useMainStore());

  const dismissedVersion = useLocalStorage<string | null>(
    `${get(loggedUserId)}.rotki.sponsorship.dismissed`,
    null,
  );

  const shouldShowSponsorship = computed<boolean>(() => {
    // Free users always see sponsorship
    if (!get(premium))
      return true;

    // Premium users: check if dismissed and version
    const dismissed = get(dismissedVersion);

    // If never dismissed, show it
    if (!dismissed)
      return true;

    const currentVersion = get(appVersion);

    // If it's a major or minor update, show again
    return isMajorOrMinorUpdate(currentVersion, dismissed);
  });

  const dismissSponsorship = (): void => {
    if (!get(premium))
      return;

    const currentVersion = get(appVersion);
    set(dismissedVersion, currentVersion);
  };

  return {
    canDismissSponsorship: premium,
    dismissSponsorship,
    shouldShowSponsorship,
  };
}
