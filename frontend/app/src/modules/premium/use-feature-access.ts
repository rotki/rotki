import type { MaybeRefOrGetter, Ref } from 'vue';
import { PremiumFeature } from '@/modules/session/types';
import { usePremiumStore } from '@/store/session/premium';

export { PremiumFeature };

interface UseFeatureAccessReturn {
  /** Whether the user has premium and the feature is enabled for their tier */
  allowed: Readonly<Ref<boolean>>;
  /** The minimum subscription tier required for this feature, null if unknown */
  minimumTier: Readonly<Ref<string | null>>;
  /** The user's current subscription tier */
  currentTier: Readonly<Ref<string>>;
  /** Whether the user has an active premium subscription */
  premium: Readonly<Ref<boolean>>;
}

/**
 * Facade composable for checking premium feature access.
 * Combines premium status, feature capability, and tier info in one call.
 */
export function useFeatureAccess(feature: MaybeRefOrGetter<PremiumFeature>): UseFeatureAccessReturn {
  const store = usePremiumStore();
  const { capabilities, premium } = storeToRefs(store);

  const allowed = computed<boolean>(() => {
    if (!get(premium))
      return false;

    const caps = get(capabilities);
    const featureValue = toValue(feature);
    if (featureValue === PremiumFeature.CLOUD_BACKUP)
      return (caps?.maxBackupSizeMb ?? 0) > 0;

    return caps?.[featureValue]?.enabled ?? false;
  });

  const minimumTier = computed<string | null>(() => {
    const caps = get(capabilities);
    const featureValue = toValue(feature);
    if (featureValue === PremiumFeature.CLOUD_BACKUP)
      return null;

    return caps?.[featureValue]?.minimumTier ?? null;
  });

  const currentTier = computed<string>(() => get(capabilities)?.currentTier ?? 'Free');

  return {
    allowed: readonly(allowed),
    currentTier: readonly(currentTier),
    minimumTier: readonly(minimumTier),
    premium,
  };
}
