import { createAuth0Client } from '@auth0/auth0-spa-js'

const domain = import.meta.env.VITE_AUTH0_DOMAIN
const clientId = import.meta.env.VITE_AUTH0_CLIENT_ID
const audience = import.meta.env.VITE_AUTH0_AUDIENCE

export const auth0Configured = Boolean(domain && clientId && audience)

let clientPromise

function getClient() {
  if (!auth0Configured) throw new Error('Auth0 is not configured.')
  clientPromise ||= createAuth0Client({
    domain,
    clientId,
    cacheLocation: 'localstorage',
    authorizationParams: {
      audience,
      redirect_uri: window.location.origin,
    },
  })
  return clientPromise
}

export async function restoreAuth0Session() {
  const client = await getClient()
  if (window.location.search.includes('code=') && window.location.search.includes('state=')) {
    await client.handleRedirectCallback()
    window.history.replaceState({}, document.title, window.location.pathname)
  }
  if (!(await client.isAuthenticated())) return null
  const user = await client.getUser()
  const accessToken = await client.getTokenSilently()
  return { user, access_token: accessToken }
}

export async function signInWithAuth0(signUp = false) {
  const client = await getClient()
  await client.loginWithRedirect({
    authorizationParams: signUp ? { screen_hint: 'signup' } : undefined,
  })
}

export async function getAuth0AccessToken() {
  if (!auth0Configured) return null
  return (await getClient()).getTokenSilently()
}

export async function signOutAuth0() {
  const client = await getClient()
  client.logout({ logoutParams: { returnTo: window.location.origin } })
}
