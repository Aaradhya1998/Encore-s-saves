/**
 * EnCore's SnapSave - Supabase Auth Client
 * Optional passwordless authentication matching DoYour To-Do.
 * Auth is completely skippable for local development and instant downloads.
 */

const SUPABASE_CONFIG = {
  url: "https://YOUR-PROJECT-ID.supabase.co",
  anonKey: "YOUR_SUPABASE_ANON_KEY_HERE"
};

const SupabaseClient = (function () {
  let client = null;

  function isConfigured() {
    const isUrlPlaceholder = !SUPABASE_CONFIG.url ||
      SUPABASE_CONFIG.url.includes("YOUR-PROJECT-ID") ||
      SUPABASE_CONFIG.url.trim() === "";
    const isKeyPlaceholder = !SUPABASE_CONFIG.anonKey ||
      SUPABASE_CONFIG.anonKey.includes("YOUR_SUPABASE_ANON_KEY") ||
      SUPABASE_CONFIG.anonKey.trim() === "";
    return !isUrlPlaceholder && !isKeyPlaceholder;
  }

  function getClient() {
    if (!client && isConfigured() && window.supabase && window.supabase.createClient) {
      client = window.supabase.createClient(SUPABASE_CONFIG.url, SUPABASE_CONFIG.anonKey);
    }
    return client;
  }

  async function getSession() {
    // Check local guest bypass or mock session first
    const guestUser = localStorage.getItem("snapsave_guest_user");
    if (guestUser) {
      return { session: { user: { email: guestUser } } };
    }

    const sb = getClient();
    if (!sb) return { session: null };
    return await sb.auth.getSession();
  }

  async function signInWithEmail(email) {
    const sb = getClient();
    if (!sb) {
      // If not configured, allow local guest session
      localStorage.setItem("snapsave_guest_user", email);
      return { data: { user: { email } }, error: null };
    }
    return await sb.auth.signInWithOtp({
      email: email,
      options: {
        emailRedirectTo: window.location.origin + window.location.pathname.replace("login.html", "index.html")
      }
    });
  }

  async function signOut() {
    localStorage.removeItem("snapsave_guest_user");
    const sb = getClient();
    if (sb) {
      await sb.auth.signOut();
    }
    return true;
  }

  function onAuthStateChange(callback) {
    const sb = getClient();
    if (!sb) return { data: { subscription: { unsubscribe: () => {} } } };
    return sb.auth.onAuthStateChange(callback);
  }

  return {
    isConfigured,
    getClient,
    getSession,
    signInWithEmail,
    signOut,
    onAuthStateChange
  };
})();

window.SupabaseClient = SupabaseClient;
