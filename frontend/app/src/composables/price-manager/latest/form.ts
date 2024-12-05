import { useForm } from '@/composables/form';

export const useLatestPriceForm = createSharedComposable(useForm<boolean>);
