import {SUPABASE_URL, SUPABASE_ANON_KEY, BRIDGE, configured} from './config.js';

export const byId = id => document.getElementById(id);
export const labels = {
  waiting: 'En sala de espera', token_sent: 'Token recibido', link_requested: 'Solicitando enlace',
  active: 'Túnel activo', paused: 'Pausado', stopped: 'Detenido'
};

export function element(tag, content) {
  const item = document.createElement(tag);
  if (content != null) item.textContent = content;
  return item;
}

export function note(message) {
  const node = byId('notice');
  if (!node) return;
  node.textContent = message;
  node.hidden = !message;
}

export function unwrap(result) {
  if (result.error) throw new Error(result.error.message);
  return result.data;
}

const busyControls = new WeakSet();

export function safe(operation) {
  return async event => {
    event?.preventDefault();
    const control = event?.submitter || (event?.currentTarget instanceof HTMLButtonElement ? event.currentTarget : null);
    if (control && busyControls.has(control)) return;
    if (control) {
      busyControls.add(control);
      control.setAttribute('aria-busy','true');
    }
    try {
      await operation(event);
    } catch (error) {
      note(error.message);
    } finally {
      if (control) {
        busyControls.delete(control);
        control.removeAttribute('aria-busy');
      }
    }
  };
}

export function messages(list, rows, role) {
  const key = JSON.stringify(rows);
  if (list.dataset.rendered === key) return;
  list.dataset.rendered = key;
  const bottom = list.scrollHeight - list.scrollTop - list.clientHeight < 48;
  const fragment = document.createDocumentFragment();
  for (const row of [...rows].reverse()) {
    const item = element('li');
    item.dataset.own = String(row.sender === role);
    item.append(element('strong', row.sender === 'tech' ? 'Técnico' : 'Usuario'),
      element(row.is_token ? 'code' : 'span', row.content));
    fragment.append(item);
  }
  if (!rows.length) fragment.append(element('li', 'Aún no hay mensajes en esta conversación.'));
  list.replaceChildren(fragment);
  if (bottom) list.scrollTop = list.scrollHeight;
}

export function live(client, tables, update) {
  let pending = false;
  let running = false;
  const refresh = async () => {
    if (running) { pending = true; return; }
    running = true;
    try { await update(); } catch (error) { note(error.message); }
    finally {
      running = false;
      if (pending) { pending = false; setTimeout(refresh, 100); }
    }
  };
  const channel = client.channel('factory-' + crypto.randomUUID());
  for (const [table, filter] of tables) {
    channel.on('postgres_changes', {event: '*', schema: 'public', table, ...(filter ? {filter} : {})}, refresh);
  }
  channel.subscribe(status => { if (status === 'SUBSCRIBED') void refresh(); });
  const timer = setInterval(refresh, 5000);
  window.addEventListener('pagehide', () => { clearInterval(timer); void client.removeChannel(channel); }, {once:true});
  void refresh();
  return refresh;
}

async function loopback(path, data, csrf) {
  if (!csrf.value) throw new Error('Ingresa el código de la terminal.');
  let response;
  try {
    response = await fetch(BRIDGE + path, {
      method: 'POST', mode: 'cors', credentials: 'omit', redirect: 'error',
      headers: {'Content-Type': 'application/json', 'X-Factory-CSRF': csrf.value},
      body: JSON.stringify(data), signal: AbortSignal.timeout(14000)
    });
  } catch {
    throw new Error('No se alcanzó el agente local. Verifica que esté iniciado y que el navegador permita acceso a la red local.');
  }
  const result = await response.json();
  if (!response.ok) throw new Error(result.error);
  return result;
}

function initializeVisitor(client, id) {
  const form = byId('pair-form');
  const name = byId('visitor-name');
  const list = byId('visitor-messages');
  const status = byId('connection') || byId('lab-link');
  let visitorName = localStorage.getItem('compressos-visitor-name') || 'Visitante';
  if (name) name.value = visitorName;
  async function presence() {
    unwrap(await client.rpc('factory_presence', {p_name: visitorName}));
  }
  async function update() {
    const requests = [client.from('factory_lobby').select('status,device_id').eq('session_id',id).maybeSingle()];
    if (list) requests.push(client.from('factory_messages').select('id,sender,content,is_token').eq('session_id',id).order('id',{ascending:false}).limit(100));
    const [state, inbox] = await Promise.all(requests);
    const row = unwrap(state);
    status.textContent = labels[row?.status] || labels.waiting;
    if (inbox) messages(list, unwrap(inbox), 'user');
    if (form) {
      byId('pair-button').disabled = row?.status !== 'token_sent';
      byId('consent').disabled = !row?.device_id || !['link_requested','active','paused'].includes(row.status);
    }
  }
  let pinging = false;
  async function ping() {
    if (pinging) return;
    pinging = true;
    try { await presence(); } catch (error) { note(error.message); }
    finally { pinging = false; }
  }
  void ping().then(update).catch(error => note(error.message));
  const timer = setInterval(ping, 5000);
  window.addEventListener('pagehide', () => clearInterval(timer), {once:true});
  const refresh = live(client, [['factory_lobby','session_id=eq.'+id], ...(list ? [['factory_messages','session_id=eq.'+id]] : [])], update);
  if (name) byId('name-form').onsubmit = safe(async () => {
    visitorName = name.value.trim() || 'Visitante';
    localStorage.setItem('compressos-visitor-name', visitorName);
    await presence();
  });
  if (list) byId('visitor-send').onsubmit = safe(async event => {
    const input = event.currentTarget.elements.text;
    const sent = input.value;
    unwrap(await client.rpc('factory_send',{p_session:id,p_text:sent}));
    if (input.value === sent) input.value = '';
    await refresh();
  });
  if (!form) return;
  const csrf = byId('csrf');
  const service = byId('allow-service');
  const diagnostics = byId('allow-diagnostics');
  const consent = () => ({service:service.checked, diagnostics:diagnostics.checked});
  function showConsent(result) {
    service.checked = result.service;
    diagnostics.checked = result.diagnostics;
  }
  form.onsubmit = safe(async () => {
    const result = await loopback('/pair', {...consent(), session:id, token:form.elements.token.value.trim()}, csrf);
    showConsent(result);
    form.elements.token.value = '';
    note('Solicitud enviada. El técnico puede activar el enlace.');
    await update();
  });
  byId('consent').onclick = safe(async () => {
    showConsent(await loopback('/consent', consent(), csrf));
    note('Permisos locales actualizados.');
    await refresh();
  });
  byId('disconnect').onclick = safe(async () => {
    const results = await Promise.allSettled([
      csrf.value ? loopback('/disconnect', {}, csrf) : Promise.reject(new Error('Código local ausente')),
      client.rpc('factory_disconnect').then(unwrap)
    ]);
    if (results[1].status === 'rejected') throw results[1].reason;
    const local = results[0];
    if (local.status === 'fulfilled') {
      note(local.value.stopped ? 'Enlace revocado y puente desconectado.' : 'Enlace revocado. Revisa los servicios en la terminal local.');
    } else {
      note('Acceso revocado en Supabase. Si el agente sigue activo, detenlo con Ctrl+C en su terminal.');
    }
    csrf.value = '';
    await refresh();
  });
}

async function main() {
  const technician = Boolean(byId('technician')) && new URLSearchParams(location.search).get('rol') === 'tecnico';
  const status = byId('connection') || byId('lab-link');
  const quick = byId('quickstart');
  if (technician) {
    byId('visitor').hidden = true;
    byId('technician-login').hidden = false;
    byId('page-title').textContent = 'Panel del técnico';
    byId('page-description').textContent = 'Atiende conversaciones y solicitudes de soporte.';
  }
  if (!configured()) {
    status.textContent = 'Supabase pendiente';
    note('La mensajería y el enlace requieren la configuración del proyecto Supabase. El Laboratorio está disponible.');
    for (const form of document.querySelectorAll('#name-form, #visitor-send, #pair-form, #login')) {
      for (const field of form.elements) field.disabled = true;
    }
    if (byId('disconnect')) byId('disconnect').disabled = true;
    return;
  }
  if (quick) quick.textContent = 'FACTORY_ALLOW_SERVICE_CONTROL=0 FACTORY_ALLOW_REMOTE_DIAGNOSTICS=1 \\\npython3 agent.py --supabase-url ' + SUPABASE_URL + ' --anon-key ' + SUPABASE_ANON_KEY;
  await import('./supabase-client.js');
  const client = globalThis.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    auth: { storageKey: technician ? 'compressos-factory-tech' : 'compressos-factory-visitor', detectSessionInUrl:false }
  });
  if (technician) {
    const {initializeTechnician} = await import('./factory.js');
    await initializeTechnician(client);
    return;
  }
  let session = unwrap(await client.auth.getSession()).session;
  if (!session) {
    const result = await client.auth.signInAnonymously();
    if (result.error?.code === 'anonymous_provider_disabled') {
      status.textContent = 'Chat de visitantes deshabilitado';
      note('El chat de soporte todavía no admite visitantes. El acceso técnico y el Laboratorio siguen disponibles en el menú.');
      for (const field of byId('visitor')?.querySelectorAll('button, input') ?? []) field.disabled = true;
      return;
    }
    session = unwrap(result).session;
  }
  if (!session?.user?.is_anonymous) throw new Error('No fue posible iniciar una sesión de visitante.');
  initializeVisitor(client, session.user.id);
}

window.addEventListener('pageshow', event => {
  if (event.persisted) location.reload();
});

if (byId('connection') || byId('lab-link')) {
  main().catch(error => {
    (byId('connection') || byId('lab-link')).textContent = 'Sin conexión';
    note(error.message);
  });
}
