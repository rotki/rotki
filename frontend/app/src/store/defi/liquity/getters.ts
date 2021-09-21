import { LiquitityState } from '@/store/defi/liquity/types';
import { RotkehlchenState } from '@/store/types';
import { Getters } from '@/store/typing';

interface LiquityGetters {}

export const getters: Getters<
  LiquitityState,
  LiquityGetters,
  RotkehlchenState,
  any
> = {};
