// Centralized management of all API endpoints for frontend.
// Add new endpoints here.

export const API = {
  USER: {
    INFO: "/user/info",
    UPDATE: "/user/update",
    CHANGE_PASSWORD: "/user/change-password",
  },
  ADMIN: {
    USERS: {
      LIST: "/admin/users",
      CREATE: "/admin/users",
      UPDATE: "/admin/users/:id",
      DELETE: "/admin/users/:id",
      RESET_PASSWORD: "/admin/users/:id/reset-password",
    },
    ROLES: {
      LIST: "/admin/roles",
      CREATE: "/admin/roles",
      UPDATE: "/admin/roles/:role_name",
      DELETE: "/admin/roles/:role_name",
      UPDATE_ATTRIBUTES: "/admin/roles/:role_name/attributes",
    },
  },
  DEBUG: {
    TEST_IP: "/debug/test-ip",
    CLEAR_BLOCKED_IPS: "/debug/clear-blocked-ip",
  },
  WEBPUSH: {
    SUBSCRIBE: "/webpush/subscribe",
    UNSUBSCRIBE: "/webpush/unsubscribe",
    SUBSCRIPTIONS: "/webpush/subscriptions",
  },
};

export default API;