import { useForm } from '@/composables/form';

export const useHistoricPriceForm = createSharedComposable(useForm<boolean>);
