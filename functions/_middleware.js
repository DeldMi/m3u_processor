export async function onRequest(context) {
    const incoming = new URL(context.request.url);
    const pathname = incoming.pathname;
    const backendPaths = pathname.startsWith('/api/') ||
        pathname === '/login' ||
        pathname === '/logout' ||
        pathname.startsWith('/playlist/') ||
        pathname.startsWith('/epg/');

    if (!backendPaths) return context.next();

    const backendOrigin = context.env.BACKEND_ORIGIN;
    if (!backendOrigin) {
        return new Response(JSON.stringify({ error: 'BACKEND_ORIGIN não configurado no Cloudflare Pages.' }), {
            status: 503,
            headers: { 'content-type': 'application/json; charset=utf-8' },
        });
    }

    const backend = new URL(backendOrigin);
    backend.pathname = pathname;
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
