async function request(method, path, body) {
  const r = await fetch(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!r.ok) {
    let detail = `${r.status} ${r.statusText}`
    try { detail = (await r.json()).detail || detail } catch { /* keep status text */ }
    throw new Error(detail)
  }
  if (r.status === 204) return null
  return r.json()
}
export const getJSON = (path) => request('GET', path)
export const postJSON = (path, body) => request('POST', path, body)
export const putJSON = (path, body) => request('PUT', path, body)
