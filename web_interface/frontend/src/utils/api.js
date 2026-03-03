// utils/api.js

const BASE_URL = ''; // Relative path assumption
let API_KEY = '';
let CURRENT_INSTANCE = 'main';

export const initApi = async () => {
    try {
        const res = await fetch(\`\${BASE_URL}/admin_config.json\`);
        const data = await res.json();
        API_KEY = data.apiKey || '';
        console.log("API Key loaded successfully.");
    } catch (e) {
        console.warn("Failed to load API config:", e);
    }
};

export const setInstance = (instance) => {
    CURRENT_INSTANCE = instance;
};

const fetchApi = async (endpoint, method = 'GET', body = null) => {
    const url = new URL(\`\${window.location.origin}\${BASE_URL}\${endpoint}\`);
    url.searchParams.append('key', API_KEY);
    url.searchParams.append('instance_id', CURRENT_INSTANCE);
    
    const options = { method };
    if (body) {
        options.headers = { 'Content-Type': 'application/json' };
        // Ensure API key and instance_id are included in POST body too if required by backend
        options.body = JSON.stringify({ ...body, key: API_KEY, instance_id: CURRENT_INSTANCE });
    }

    const res = await fetch(url.toString(), options);
    if (!res.ok) throw new Error(\`HTTP error! status: \${res.status}\`);
    return await res.json();
};

export const fetchStatus = () => fetchApi('/api/status');
export const sendCommandToConsole = (cmd) => fetchApi('/api/command', 'POST', { cmd });
export const sendPowerAction = (action) => fetchApi(\`/api/\${action}\`, 'POST'); // start, stop, kill
