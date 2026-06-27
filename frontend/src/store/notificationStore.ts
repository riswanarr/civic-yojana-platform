import { create } from "zustand";
import { apiClient } from "@/services/apiClient";
import { useAuthStore } from "@/store/authStore";
import type { Notification, NotificationsResponse } from "@/types";

type NotificationState = {
  notifications: Notification[];
  unreadCount: number;
  isLoading: boolean;
  error: string | null;
  fetchNotifications: () => Promise<void>;
  markAsRead: (notificationId: string) => Promise<void>;
  resetNotifications: () => void;
};

function getAccessToken() {
  return useAuthStore.getState().session?.access_token;
}

export const useNotificationStore = create<NotificationState>((set) => ({
  notifications: [],
  unreadCount: 0,
  isLoading: false,
  error: null,

  fetchNotifications: async () => {
    const accessToken = getAccessToken();

    if (!accessToken) {
      set({ notifications: [], unreadCount: 0, isLoading: false, error: null });
      return;
    }

    set({ isLoading: true, error: null });

    try {
      const data = await apiClient.get<NotificationsResponse>("/notifications", accessToken);
      set({
        notifications: Array.isArray(data.items) ? data.items : [],
        unreadCount: data.unread_count ?? 0,
        isLoading: false,
        error: null
      });
    } catch (error) {
      set({
        notifications: [],
        unreadCount: 0,
        isLoading: false,
        error: error instanceof Error ? error.message : "Unable to load notifications."
      });
    }
  },

  markAsRead: async (notificationId) => {
    const accessToken = getAccessToken();

    if (!accessToken) {
      return;
    }

    try {
      const updatedNotification = await apiClient.patch<Notification>(
        `/notifications/${notificationId}/read`,
        {},
        accessToken
      );

      set((state) => {
        const notifications = state.notifications.map((notification) =>
          notification.id === notificationId ? updatedNotification : notification
        );

        return {
          notifications,
          unreadCount: notifications.filter((notification) => !notification.is_read).length,
          error: null
        };
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Unable to update notification."
      });
    }
  },

  resetNotifications: () => {
    set({ notifications: [], unreadCount: 0, isLoading: false, error: null });
  }
}));
