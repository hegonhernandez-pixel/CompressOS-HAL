// Clave publishable o JWT anon del proyecto nuevo. Este archivo se distribuye públicamente.
export const SUPABASE_URL = 'https://kpwumjotcnteygymqlmf.supabase.co';
export const SUPABASE_ANON_KEY = 'sb_publishable_LhiYfeK1DjTluheZFoAqfQ_39ebydsl';
export const BRIDGE = 'http://127.0.0.1:7890';
export const LEGACY_TEAM = 'https://compresso-lab-local.whitespoonbill5.chatgpt.site/mensajes';
export const ACTIONS = ['status', 'uptime', 'disk', 'systemctl', 'swapon', 'hal_metrics'];

export function configured() {
  if (!/^https:\/\/[a-z0-9]+\.supabase\.co$/.test(SUPABASE_URL)) return false;
  if (/^sb_publishable_[\w-]+$/.test(SUPABASE_ANON_KEY)) return true;
  try {
    const payload = SUPABASE_ANON_KEY.split('.')[1].replaceAll('-', '+').replaceAll('_', '/');
    return JSON.parse(atob(payload)).role === 'anon';
  } catch {
    return false;
  }
}
