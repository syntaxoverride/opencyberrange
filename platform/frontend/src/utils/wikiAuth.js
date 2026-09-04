// Keep the wiki_auth cookie in sync with the current JWT so the nginx
// auth_request gates in front of the course wikis always have a valid token to
// validate.
//
// Scope: the cookie is bound to the app's OWN hostname via Domain, which per
// RFC 6265 sends it to that host AND its subdomains only, NOT to sibling hosts
// elsewhere on the registrable domain. So a subdomain gated by the same OCR
// login receives the token, and no other service on the platform domain does.
// On an IP or localhost it stays host-only.
//
// IMPORTANT: every place that sets wiki_auth must use THIS helper. Setting the
// same cookie name with a different Domain creates a second, separate cookie and
// nginx then reads an arbitrary one. One helper keeps the scope consistent.
export function setWikiAuthCookie() {
  const token = localStorage.getItem('token')
  if (!token) return
  const host = window.location.hostname
  const isIp = /^\d{1,3}(\.\d{1,3}){3}$/.test(host)
  // Bind to the app's own host (covers only this instance's subdomains).
  const domainAttr = (!isIp && host !== 'localhost' && host.includes('.'))
    ? `; Domain=${host}` : ''
  document.cookie = `wiki_auth=${token}; path=/; SameSite=Lax; max-age=86400${domainAttr}`
}
