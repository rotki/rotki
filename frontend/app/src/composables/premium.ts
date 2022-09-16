import { set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { usePremiumStore } from '@/store/session/premium';

export const getPremium = () => {
  const { premium } = storeToRefs(usePremiumStore());
  return premium;
};

export const setPremium = (isPremium: boolean) => {
  const { premium } = storeToRefs(usePremiumStore());
  set(premium, isPremium);
};
