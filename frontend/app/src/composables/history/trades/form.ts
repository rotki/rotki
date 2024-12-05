import { useForm } from '@/composables/form';

export const useTradesForm = createSharedComposable(useForm<boolean>);
