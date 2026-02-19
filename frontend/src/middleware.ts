import type { MiddlewareHandler } from 'astro';

/**
 * Proxy /api requests to the backend service.
 *
 * In development, Vite's built-in proxy handles this (see astro.config.mjs).
 * In production Docker, this middleware forwards /api/* to the backend container
 * so the browser only talks to one origin.
 */

const API_BACKEND = import.meta.env.API_URL || process.env.API_URL || 'http://localhost:8000';

export const onRequest: MiddlewareHandler = async (context, next) => {
    const url = new URL(context.request.url);

    if (!url.pathname.startsWith('/api/')) {
        return next();
    }

    const backendUrl = `${API_BACKEND}${url.pathname}${url.search}`;

    const headers = new Headers(context.request.headers);
    // Remove host header to avoid backend confusion
    headers.delete('host');

    const init: RequestInit = {
        method: context.request.method,
        headers,
    };

    if (!['GET', 'HEAD'].includes(context.request.method)) {
        init.body = context.request.body;
        // @ts-expect-error -- duplex required for streaming body in Node.js
        init.duplex = 'half';
    }

    try {
        const upstream = await fetch(backendUrl, init);

        return new Response(upstream.body, {
            status: upstream.status,
            statusText: upstream.statusText,
            headers: upstream.headers,
        });
    } catch {
        return new Response(JSON.stringify({ detail: 'Backend unavailable' }), {
            status: 502,
            headers: { 'Content-Type': 'application/json' },
        });
    }
};
