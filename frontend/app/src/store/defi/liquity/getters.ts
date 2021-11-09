import { LiquityState } from '@/store/defi/liquity/types';
import { RotkehlchenState } from '@/store/types';
import { Getters } from '@/store/typing';

interface LiquityGetters {}

export const getters: Getters<
  LiquityState,
  LiquityGetters,
  RotkehlchenState,
  any
> = {};
