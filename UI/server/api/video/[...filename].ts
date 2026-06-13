import http from 'node:http'

export default defineEventHandler(async (event) => {
  const filename = getRouterParam(event, 'filename') || ''

  const forwardHeaders = getRequestHeaders(event)
  forwardHeaders.host = 'localhost:8080'

  return new Promise((resolve, reject) => {
    const req = http.request(
      {
        hostname: 'localhost',
        port: 8080,
        path: `/api/video/${filename}`,
        method: event.method,
        headers: forwardHeaders,
      },
      (proxyRes) => {
        event.node.res.writeHead(proxyRes.statusCode || 200, proxyRes.headers as Record<string, string | string[]>)
        proxyRes.pipe(event.node.res)
        proxyRes.on('end', () => resolve())
      }
    )

    req.on('error', (err: NodeJS.ErrnoException) => {
      reject(createError({ statusCode: 502, statusMessage: `Backend error: ${err.message}` }))
    })

    req.end()
  })
})
