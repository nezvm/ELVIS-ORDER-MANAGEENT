/**
 * Simple proxy server to forward all requests to Django backend
 * This is needed because Emergent platform routes non-/api traffic to frontend port 3000
 */
const http = require('http');
const httpProxy = require('http-proxy');

const proxy = httpProxy.createProxyServer({});
const BACKEND_URL = 'http://127.0.0.1:8001';

proxy.on('error', (err, req, res) => {
    console.error('Proxy error:', err);
    res.writeHead(502, { 'Content-Type': 'text/plain' });
    res.end('Backend unavailable');
});

const server = http.createServer((req, res) => {
    console.log(`Proxying: ${req.method} ${req.url}`);
    proxy.web(req, res, { target: BACKEND_URL });
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, '0.0.0.0', () => {
    console.log(`Frontend proxy server listening on port ${PORT}`);
    console.log(`Forwarding all requests to ${BACKEND_URL}`);
});
