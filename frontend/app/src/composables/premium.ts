import { usePremiumStore } from '@/store/session/premium';

export const usePremium = () => {
  const { premium } = storeToRefs(usePremiumStore());
  return premium;
};
