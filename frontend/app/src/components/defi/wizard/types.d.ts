import { Module } from '@/services/session/consts';

export interface SupportedModule {
  name: string;
  icon: string;
  identifier: Module;
}
