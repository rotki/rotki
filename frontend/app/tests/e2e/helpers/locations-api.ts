import type { APIRequestContext } from '@playwright/test';
import { backendUrl } from '../../../playwright.config';

export interface ApiLocationNode {
  identifier: string;
  name: string;
  parent_identifier: string | null;
  is_builtin: boolean;
  is_active: boolean;
  image: string | null;
}

export interface ApiLocationAlias {
  alias: string;
  location_identifier: string;
}

async function apiResult<T>(request: APIRequestContext, path: string): Promise<T> {
  const response = await request.get(`${backendUrl}/api/1${path}`);
  const body: { result: T } = await response.json();
  return body.result;
}

/** The whole location tree as the backend stores it, built-in and custom nodes alike. */
export async function apiLocationTree(request: APIRequestContext): Promise<ApiLocationNode[]> {
  return apiResult<ApiLocationNode[]>(request, '/locations');
}

/** The custom location with the given name, or undefined when there is none. */
export async function apiCustomLocation(request: APIRequestContext, name: string): Promise<ApiLocationNode | undefined> {
  const tree = await apiLocationTree(request);
  return tree.find(node => !node.is_builtin && node.name === name);
}

export async function apiLocationAliases(request: APIRequestContext): Promise<ApiLocationAlias[]> {
  return apiResult<ApiLocationAlias[]>(request, '/locations/aliases');
}
