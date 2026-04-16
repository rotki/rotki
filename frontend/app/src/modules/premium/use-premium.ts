import type { Ref } from 'vue';
import { usePremiumStore } from '@/modules/premium/use-premium-store';

export function usePremium(): Ref<boolean> {
  const { premium } = storeToRefs(usePremiumStore());
  return premium;
}
