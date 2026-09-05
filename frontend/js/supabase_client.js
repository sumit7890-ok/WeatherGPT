/**
 * WeatherGPT - Supabase Integration Client Module
 * Handles:
 * - Authentication (Sign Up, Sign In, Sign Out, Password Reset)
 * - User Profile Synchronization
 * - User Chat History Isolation
 * - Bookmarked / Saved Locations
 * - User Feedback
 * - Graceful fallback to local guest session if unauthenticated or Supabase URL pending
 */

const SupabaseService = {
  client: null,
  currentUser: null,
  isConfigured: false,
  authListeners: [],

  async init() {
    try {
      // 1. Fetch publishable configuration from backend
      const res = await fetch("/api/supabase/config");
      if (!res.ok) return false;
      const cfg = await res.json();

      const url = cfg.supabase_url;
      const key = cfg.supabase_publishable_key;

      if (!url || !key || url.includes("your-project") || url.length < 10) {
        console.info("Supabase URL pending configuration in .env. Operating in guest / local mode.");
        this.isConfigured = false;
        return false;
      }

      // 2. Verify Supabase SDK is available
      if (typeof window.supabase === "undefined" || !window.supabase.createClient) {
        console.warn("Supabase JS SDK not loaded yet.");
        return false;
      }

      // 3. Initialize Supabase Client
      this.client = window.supabase.createClient(url, key, {
        auth: {
          persistSession: true,
          autoRefreshToken: true,
          detectSessionInUrl: true
        }
      });

      this.isConfigured = true;

      // 4. Check existing session
      const { data: { session } } = await this.client.auth.getSession();
      if (session && session.user) {
        this.currentUser = session.user;
        this.notifyAuthChange("SIGNED_IN", this.currentUser);
      }

      // 5. Subscribe to auth events
      this.client.auth.onAuthStateChange((event, session) => {
        this.currentUser = session ? session.user : null;
        this.notifyAuthChange(event, this.currentUser);
      });

      return true;
    } catch (e) {
      console.warn("Supabase initialization error:", e);
      return false;
    }
  },

  onAuthStateChange(cb) {
    if (typeof cb === "function") {
      this.authListeners.push(cb);
    }
  },

  notifyAuthChange(event, user) {
    this.authListeners.forEach(cb => {
      try { cb(event, user); } catch (err) { console.error(err); }
    });
  },

  // ----------------------------------------------------
  // Authentication Methods
  // ----------------------------------------------------

  async signUp(email, password, fullName = "") {
    if (!this.client) throw new Error("Supabase is not configured yet. Please configure SUPABASE_URL in .env.");
    const { data, error } = await this.client.auth.signUp({
      email: email.trim(),
      password: password,
      options: {
        data: {
          full_name: fullName.trim() || email.split("@")[0]
        }
      }
    });
    if (error) throw error;
    return data;
  },

  async signIn(email, password) {
    if (!this.client) throw new Error("Supabase is not configured yet. Please configure SUPABASE_URL in .env.");
    const { data, error } = await this.client.auth.signInWithPassword({
      email: email.trim(),
      password: password
    });
    if (error) throw error;
    this.currentUser = data.user;
    return data;
  },

  async signOut() {
    if (this.client) {
      await this.client.auth.signOut();
    }
    this.currentUser = null;
    this.notifyAuthChange("SIGNED_OUT", null);
  },

  async resetPassword(email) {
    if (!this.client) throw new Error("Supabase is not configured yet.");
    const { data, error } = await this.client.auth.resetPasswordForEmail(email.trim(), {
      redirectTo: window.location.origin
    });
    if (error) throw error;
    return data;
  },

  getUser() {
    return this.currentUser;
  },

  getUserDisplayName() {
    if (!this.currentUser) return "Guest User";
    const meta = this.currentUser.user_metadata || {};
    return meta.full_name || meta.name || this.currentUser.email.split("@")[0];
  },

  // ----------------------------------------------------
  // User Chat History Methods
  // ----------------------------------------------------

  async saveChatMessage(sessionId, userQuestion, aiResponse, location) {
    if (!this.client || !this.currentUser) return null;
    try {
      const { data, error } = await this.client
        .from("chat_history")
        .insert([
          {
            user_id: this.currentUser.id,
            session_id: sessionId,
            user_question: userQuestion,
            ai_response: aiResponse,
            location: location || "India"
          }
        ]);
      if (error) {
        console.warn("Could not sync chat to Supabase:", error.message);
      }
      return data;
    } catch (e) {
      console.warn("Supabase saveChatMessage exception:", e);
      return null;
    }
  },

  async getUserChatHistory() {
    if (!this.client || !this.currentUser) return [];
    try {
      const { data, error } = await this.client
        .from("chat_history")
        .select("*")
        .eq("user_id", this.currentUser.id)
        .order("created_at", { ascending: false })
        .limit(50);
      if (error) throw error;
      return data || [];
    } catch (e) {
      console.warn("Failed to fetch Supabase chat history:", e.message);
      return [];
    }
  },

  // ----------------------------------------------------
  // Saved Locations (Bookmarks)
  // ----------------------------------------------------

  async getSavedLocations() {
    if (!this.client || !this.currentUser) {
      // Local fallback
      try {
        const stored = localStorage.getItem("weathergpt_guest_saved_locations");
        return stored ? JSON.parse(stored) : [];
      } catch {
        return [];
      }
    }
    try {
      const { data, error } = await this.client
        .from("saved_locations")
        .select("*")
        .eq("user_id", this.currentUser.id)
        .order("created_at", { ascending: false });
      if (error) throw error;
      return data || [];
    } catch (e) {
      console.warn("Error getting saved locations:", e.message);
      return [];
    }
  },

  async addSavedLocation(loc) {
    if (!this.client || !this.currentUser) {
      // Local fallback
      const stored = await this.getSavedLocations();
      const newLoc = {
        id: "loc-" + Date.now(),
        name: loc.name,
        state: loc.state || "",
        country: loc.country || "India",
        latitude: loc.latitude,
        longitude: loc.longitude,
        created_at: new Date().toISOString()
      };
      stored.unshift(newLoc);
      localStorage.setItem("weathergpt_guest_saved_locations", JSON.stringify(stored));
      return newLoc;
    }

    const { data, error } = await this.client
      .from("saved_locations")
      .insert([
        {
          user_id: this.currentUser.id,
          name: loc.name,
          state: loc.state || "",
          country: loc.country || "India",
          latitude: loc.latitude,
          longitude: loc.longitude,
          is_default: loc.is_default || false
        }
      ])
      .select();
    if (error) throw error;
    return data && data[0];
  },

  async removeSavedLocation(id) {
    if (!this.client || !this.currentUser) {
      const stored = await this.getSavedLocations();
      const filtered = stored.filter(x => x.id !== id);
      localStorage.setItem("weathergpt_guest_saved_locations", JSON.stringify(filtered));
      return true;
    }
    const { error } = await this.client
      .from("saved_locations")
      .delete()
      .eq("id", id)
      .eq("user_id", this.currentUser.id);
    if (error) throw error;
    return true;
  },

  // ----------------------------------------------------
  // User Feedback
  // ----------------------------------------------------

  async submitFeedback(rating, category, comment) {
    if (!this.client) {
      // Store local feedback acknowledgement
      console.info("Feedback received in local mode:", { rating, category, comment });
      return { status: "success", local: true };
    }
    const { data, error } = await this.client
      .from("feedback")
      .insert([
        {
          user_id: this.currentUser ? this.currentUser.id : null,
          rating: parseInt(rating, 10),
          category: category,
          comment: comment.trim()
        }
      ]);
    if (error) throw error;
    return data;
  }
};

window.SupabaseService = SupabaseService;
