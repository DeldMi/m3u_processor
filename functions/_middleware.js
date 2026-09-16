export async function onRequest(context) {
    const backendOrigin = context.env.BACKEND_ORIGIN;

    // Sem backend configurado, páginas estáticas continuam funcionando; APIs
    // retornam erro explícito em vez de vazar detalhes de configuração.
    if (!backendOrigin) {
        const pathname = new URL(context.request.url).pathname;
        if (pathname.startsWith('/api/') || pathname === '/login' || pathname === '/logout') {
            return new Response(JSON.stringify({ error: 'BACKEND_ORIGIN não configurado.' }), {
                status: 503,
                headers: { 'content-type': 'application/json; charset=utf-8' },
            });
        }
        return context.next();
    }

    const incoming = new URL(context.request.url);
    const backend = new URL(backendOrigin);
    backend.pathname = incoming.pathname;
    backend.search = incoming.search;

    const headers = new Headers(context.request.headers);
    headers.set('host', backend.host);
    headers.set('x-forwarded-host', incoming.host);
    headers.set('x-forwarded-proto', incoming.protocol.replace(':', ''));

    const request = new Request(backend.toString(), {
        method: context.request.method,
        headers,
        body: ['GET', 'HEAD'].includes(context.request.method) ? undefined : context.request.body,
        redirect: 'manual',
    });

    return fetch(request);
}
