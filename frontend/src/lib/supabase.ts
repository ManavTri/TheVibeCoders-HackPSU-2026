// Supabase browser auth is not enabled in the local demo. Keep this module as the
// integration seam; never infer that an unset configuration means authenticated.
export const supabaseConfig = {
  url: import.meta.env.VITE_SUPABASE_URL as string | undefined,
  anonKey: import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined,
}
