import {ACTIONS, LEGACY_TEAM, SUPABASE_URL, SUPABASE_ANON_KEY} from './config.js';
import {byId, labels, element, note, unwrap, safe, messages, live} from './usuario.js';

const catalog = {
  'Instalación': ['Prepara el agente Linux y verifica el vínculo con el equipo del usuario.', 'Agente Linux', './agent.py'],
  'Agentes': ['Consulta el equipo vinculado, sus permisos y su estado.', 'Equipo vinculado', '#controls'],
  'Monitor': ['Consulta CPU, memoria, disco y el estado de los servicios.', 'Ver telemetría', '#metrics'],
  'Comercial': ['Alcance del servicio para clientes Linux: instalación, diagnóstico, monitoreo y soporte.'],
  'Laboratorio / Presets Lab': ['Pruebas locales, perfiles y evidencias de IA.', 'Abrir Laboratorio', './laboratorio.html'],
  'Servicios IA': ['Registra el estado de Lemonade, AnythingLLM y los servicios de HAL durante el soporte.', 'Ver servicios', '#services'],
  'Alojamiento': ['GitHub Pages sirve el portal. Supabase autentica a los participantes y sincroniza las sesiones.'],
  'Monitoreo': ['Revisa el último contacto y el resultado de cada diagnóstico.', 'Ver seguimiento', '#action-results'],
  'Precios Factory': ['Las tarifas comerciales están pendientes de validación.'],
  'Checklist del PR': ['Verificar RLS, conversación entre dos equipos, consentimiento local, diagnóstico y revocación.'],
};

function initializeCatalog() {
  const tabs = byId('catalog-tabs');
  const content = byId('catalog-content');
  for (const [title, [description, link, href]] of Object.entries(catalog)) {
    const button = element('button', title);
    button.type = 'button';
    button.setAttribute('aria-pressed','false');
    button.onclick = () => {
      for (const item of tabs.children) {
        item.classList.toggle('active',item === button);
        item.setAttribute('aria-pressed',String(item === button));
      }
      content.replaceChildren(element('h3',title),element('p',description));
      if (link) {
        const anchor = element('a',link);
        anchor.href = href;
        content.append(anchor);
      }
    };
    tabs.append(button);
  }
  tabs.firstElementChild.click();
  const team = element('a','Mensajes internos Factory y Arcade');
  team.href = LEGACY_TEAM;
  byId('catalog').append(team);
  const operations = element('a','Registros internos de operaciones');
  operations.href = new URL('/', LEGACY_TEAM).href;
  team.after(document.createElement('br'),operations);
}

function panel(client) {
  let selected = null;
  let device = null;
  let previousLobby = '';
  const controls = [...byId('controls').querySelectorAll('button')];
  const read = (table, columns='*') => client.from(table).select(columns);
  const rpc = async (name, data) => unwrap(await client.rpc(name,data));

  const diagnosticButtons = ACTIONS.map(kind => {
    const button = element('button',kind);
    button.type = 'button';
    button.disabled = true;
    button.onclick = safe(async () => {
      await rpc('factory_enqueue',{p_device:device.device_id,p_kind:kind});
      note('Diagnóstico en cola.');
      await refresh();
    });
    return button;
  });
  byId('diagnostics').replaceChildren(...diagnosticButtons);

  async function update() {
    const rows = unwrap(await read('factory_lobby').gt('last_seen',new Date(Date.now()-30000).toISOString())
      .order('last_seen',{ascending:false}).limit(200));
    byId('visitor-count').textContent = rows.length + (rows.length === 200 ? '+' : '') + ' en línea';
    if (!selected && rows.length) selected = rows[0].session_id;
    const repeatableRows = [...rows].sort((a,b) => a.session_id.localeCompare(b.session_id));
    const lobbyKey = JSON.stringify([selected,repeatableRows.map(row => [row.session_id,row.visitor_name,row.status])]);
    if (lobbyKey !== previousLobby) {
      const list = byId('lobby');
      const focused = document.activeElement?.dataset?.session;
      list.replaceChildren();
      for (const row of repeatableRows) {
        const item = element('li');
        const button = element('button');
        button.dataset.session = row.session_id;
        button.type = 'button';
        button.setAttribute('aria-pressed',String(row.session_id === selected));
        button.append(element('span',row.visitor_name),element('small',labels[row.status]));
        button.onclick = () => { selected = row.session_id; device = null; void refresh(); };
        item.append(button);
        list.append(item);
        if (focused === row.session_id) button.focus();
      }
      if (!rows.length) list.append(element('li','No hay visitantes en línea.'));
      previousLobby = lobbyKey;
    }
    const current = selected;
    let visitor = rows.find(row => row.session_id === current);
    if (!visitor && current) visitor = unwrap(await read('factory_lobby').eq('session_id',current).maybeSingle());
    const queries = current ? [
      read('factory_messages','id,sender,content,is_token').eq('session_id',current).order('id',{ascending:false}).limit(100),
      read('factory_audit','event,detail,created_at').eq('session_id',current).order('id',{ascending:false}).limit(30)
    ] : [];
    if (visitor?.device_id) {
      queries.push(read('factory_agents').eq('device_id',visitor.device_id).maybeSingle(),
        read('factory_actions').eq('device_id',visitor.device_id).order('created_at',{ascending:false}).limit(20));
    }
    const [inbox,audit,agent,actions] = (await Promise.all(queries)).map(unwrap);
    if (selected !== current) return;
    device = agent || null;
    byId('selected-title').textContent = visitor?.visitor_name || 'Conversación';
    byId('issue').disabled = !rows.some(row => row.session_id === current && ['waiting','token_sent','stopped'].includes(row.status));
    byId('tech-send').querySelector('button').disabled = !visitor;
    byId('link-alert').hidden = visitor?.status !== 'link_requested';
    byId('link-alert').textContent = visitor ? visitor.visitor_name + ' solicita enlace' : '';
    messages(byId('tech-messages'),inbox || [],'tech');
    const recent = device?.last_heartbeat && Date.parse(device.last_heartbeat) > Date.now()-25000;
    const valid = device && !device.revoked && Date.parse(device.expires_at)>Date.now();
    const running = valid && recent && device.control_desired === 'active' && ['applied','session_only'].includes(device.control_result);
    const pending = valid && device.control_result === 'pending' && device.control_revision > 0;
    byId('device-state').textContent = !device ? 'Sin equipo' : !valid ? 'Enlace terminado'
      : !recent ? 'Sin latido reciente' : pending ? 'Esperando al agente' : device.control_result === 'unavailable'
        ? 'Servicio no disponible' : running ? 'Túnel activo' : labels[visitor.status];
    controls[0].disabled = !valid || !recent || running || pending;
    controls[1].disabled = !valid || device.control_desired !== 'active';
    controls[2].disabled = !valid;
    for (const button of diagnosticButtons) button.disabled = !running || !device.consent_remote_diagnostics;
    const snapshot = running ? device.telemetry_json : {};
    byId('metrics').replaceChildren(...[['CPU','cpu_percent'],['RAM','ram_percent'],['Disco','disk_percent']].map(([label,key]) => {
      const metric = element('div');
      metric.append(element('span',label),element('strong',typeof snapshot[key] === 'number' ? snapshot[key]+'%' : '—'));
      return metric;
    }));
    byId('services').textContent = snapshot.services || 'Sin datos';
    byId('action-results').replaceChildren(...(actions || []).map(action => {
      const row = element('article');
      const state = {pending:'Pendiente',completed:'Completado',rejected:'Rechazado'}[action.status];
      row.append(element('strong',action.kind+' · '+state));
      if (action.result_json) row.append(element('pre',JSON.stringify(action.result_json,null,2)));
      return row;
    }));
    byId('audit').replaceChildren(...(audit || []).map(row =>
      element('li',new Date(row.created_at).toLocaleString()+' · '+row.event+' · '+JSON.stringify(row.detail))));
  }

  byId('issue').onclick = safe(async () => {
    await rpc('factory_issue',{p_session:selected});
    note('Token enviado al visitante. Caduca en cinco minutos.');
    await refresh();
  });
  byId('tech-send').onsubmit = safe(async event => {
    const input = event.currentTarget.elements.text;
    const sent = input.value;
    await rpc('factory_send',{p_session:selected,p_text:sent});
    if (input.value === sent) input.value = '';
    await refresh();
  });
  for (const button of controls) button.onclick = safe(async () => {
    await rpc('factory_control',{p_device:device.device_id,p_state:button.dataset.control});
    await refresh();
  });
  byId('logout').onclick = safe(async () => { unwrap(await client.auth.signOut()); location.reload(); });
  initializeCatalog();
  const refresh = live(client,[['factory_messages'],['factory_agents'],['factory_actions'],['factory_audit']],update);
}

const TECHNICIAN_URL = 'https://hegonhernandez-pixel.github.io/CompressOS-HAL/?rol=tecnico';

function authResult(result) {
  if (result.error && /captcha/i.test(result.error.code || result.error.message || '')) {
    throw new Error('Supabase exige CAPTCHA. El administrador debe configurar el proveedor y el formulario, o corregir esa opción en Supabase.');
  }
  return unwrap(result);
}

export async function initializeTechnician(client, emailLink) {
  const login = byId('technician-login');
  const status = byId('connection');
  const authorized = async () => unwrap(await client.rpc('factory_is_tech'));
  function open() {
    login.hidden = true;
    byId('technician').hidden = false;
    status.textContent = 'Técnico autenticado';
    note('');
    panel(client);
  }
  const passwordLogin = byId('login');
  const google = byId('login-google');
  const resetRequest = byId('reset-request');
  const verifyLink = byId('verify-email-link');
  const newPassword = byId('new-password');
  status.textContent = 'Acceso protegido';

  const cooldownKey = 'compressos-factory-reset-after';
  byId('reset-email').onsubmit = safe(async event => {
    if (Date.now() < Number(sessionStorage.getItem(cooldownKey))) {
      throw new Error('Espera un minuto antes de solicitar otro enlace. Abre el último correo en este mismo navegador.');
    }
    const email = event.currentTarget.elements.email.value.trim();
    const result = await client.auth.resetPasswordForEmail(email,{redirectTo:TECHNICIAN_URL});
    if (result.error?.status === 429 || result.error?.code === 'over_email_send_rate_limit') {
      sessionStorage.setItem(cooldownKey,String(Date.now()+60000));
      throw new Error('Supabase limitó temporalmente los correos. Evita más intentos seguidos y espera a que se restablezca el límite.');
    }
    authResult(result);
    sessionStorage.setItem(cooldownKey,String(Date.now()+60000));
    note('Si el correo corresponde a una cuenta, recibirás un enlace. Abre el más reciente en este mismo navegador.');
  });

  function showRecovery() {
    passwordLogin.hidden = google.hidden = resetRequest.hidden = verifyLink.hidden = true;
    newPassword.hidden = false;
    status.textContent = 'Crea una contraseña nueva';
    newPassword.elements.password.focus();
  }
  async function requireTechnician(session) {
    if (session && await authorized()) return;
    if (session) unwrap(await client.auth.signOut({scope:'local'}));
    throw new Error('El enlace no corresponde a una cuenta con permiso técnico.');
  }
  async function finishCallback(session,recovery) {
    await requireTechnician(session);
    if (recovery) showRecovery();
    else open();
  }
  newPassword.onsubmit = safe(async event => {
    const form = event.currentTarget;
    if (form.elements.password.value !== form.elements.confirm.value) throw new Error('Las contraseñas deben coincidir.');
    const {session} = unwrap(await client.auth.getSession());
    await requireTechnician(session);
    authResult(await client.auth.updateUser({password:form.elements.password.value}));
    form.reset();
    unwrap(await client.auth.signOut({scope:'local'}));
    newPassword.hidden = true;
    passwordLogin.hidden = google.hidden = resetRequest.hidden = false;
    status.textContent = 'Acceso protegido';
    note('Contraseña actualizada. Entra con tu correo y la nueva contraseña.');
  });

  if (emailLink?.error) note('El enlace del correo venció o ya se usó. Solicita uno nuevo si necesitas cambiar tu contraseña.');
  if (emailLink?.token && ['recovery','signup','email'].includes(emailLink.type)) {
    passwordLogin.hidden = google.hidden = resetRequest.hidden = true;
    verifyLink.hidden = false;
    verifyLink.onsubmit = safe(async () => {
      try {
        const {session} = authResult(await client.auth.verifyOtp({type:emailLink.type,token_hash:emailLink.token}));
        await finishCallback(session,emailLink.type === 'recovery');
      } catch (error) {
        verifyLink.hidden = true;
        passwordLogin.hidden = google.hidden = resetRequest.hidden = false;
        throw error;
      }
    });
  } else if (emailLink?.code || emailLink?.legacySession) {
    try {
      const result = emailLink.code ? await client.auth.exchangeCodeForSession(emailLink.code) :
        await client.auth.setSession(emailLink.legacySession);
      if (result.error?.code === 'flow_state_not_found' || result.error?.code === 'bad_code_verifier') {
        throw new Error('Abre el enlace más reciente en el mismo navegador donde solicitaste la recuperación.');
      }
      const {session,redirectType} = authResult(result);
      await finishCallback(session,Boolean(emailLink.legacySession) || redirectType === 'PASSWORD_RECOVERY');
      if (byId('technician').hidden === false) return;
    } catch (error) {
      note(error.message);
    }
  }

  const {session} = unwrap(await client.auth.getSession());
  if (session && !emailLink) {
    if (await authorized()) {
      open();
      return;
    }
    unwrap(await client.auth.signOut({scope:'local'}));
    note('La sesión anterior no tiene permiso técnico. Entra con la cuenta autorizada.');
  }
  google.onclick = safe(async () => {
    const settings = await fetch(SUPABASE_URL + '/auth/v1/settings', {headers:{apikey:SUPABASE_ANON_KEY}});
    if (!settings.ok) throw new Error('No se pudo comprobar Google. Usa correo y contraseña.');
    if (!(await settings.json()).external?.google) throw new Error('Google aún no está habilitado. Usa correo y contraseña.');
    const redirectTo = new URL('./?rol=tecnico', location.href).href;
    const result = await client.auth.signInWithOAuth({
      provider:'google', options:{redirectTo, skipBrowserRedirect:true}
    });
    const {url} = unwrap(result);
    if (!url) throw new Error('Google no devolvió una URL de acceso. Usa correo y contraseña.');
    const destination = new URL(url);
    if (destination.origin !== new URL(SUPABASE_URL).origin) {
      throw new Error('Supabase devolvió una URL de acceso inesperada.');
    }
    location.assign(destination);
  });
  passwordLogin.onsubmit = safe(async event => {
    const form = event.currentTarget;
    try {
      authResult(await client.auth.signInWithPassword({email:form.elements.email.value,password:form.elements.password.value}));
      if (!await authorized()) {
        await client.auth.signOut();
        throw new Error('La cuenta no está autorizada como técnico.');
      }
      open();
    } finally {
      form.elements.password.value = '';
    }
  });
}
