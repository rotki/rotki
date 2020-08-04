import { SupportedModules } from '@/services/session/types';

export interface Module {
  name: string;
  displayName: string;
  icon: string;
  identifier: SupportedModules;
}
