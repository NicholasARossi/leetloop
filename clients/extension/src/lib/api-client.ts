/**
 * API client for Chrome Extension
 * Thin fetch wrapper that auto-attaches Bearer auth tokens
 */

import { getValidAccessToken } from './auth-store';

declare const __API_URL__: string;
const API_URL = typeof __API_URL__ !== 'undefined' ? __API_URL__ : '';

/**
 * Make an authenticated API request
 */
export async function apiRequest(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const apiUrl = API_URL || (await getApiUrlFromConfig());
  if (!apiUrl) {
    throw new Error('API URL not configured');
  }

  const token = await getValidAccessToken();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  return fetch(`${apiUrl}${path}`, {
    ...options,
    headers,
  });
}

async function getApiUrlFromConfig(): Promise<string> {
  const result = await chrome.storage.local.get('config');
  return result.config?.apiUrl || '';
}
