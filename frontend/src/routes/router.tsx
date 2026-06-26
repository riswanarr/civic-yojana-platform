import { createBrowserRouter, Navigate } from "react-router-dom";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { AppLayout } from "@/layouts/AppLayout";
import { AdminPage } from "@/pages/AdminPage";
import { ApplicationsPage } from "@/pages/ApplicationsPage";
import { ChatbotPage } from "@/pages/ChatbotPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { ProfilePage } from "@/pages/ProfilePage";
import { LoginPage } from "@/pages/LoginPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { SavedSchemesPage } from "@/pages/SavedSchemesPage";
import { SchemeDetailPage } from "@/pages/SchemeDetailPage";
import { SchemesPage } from "@/pages/SchemesPage";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/register", element: <RegisterPage /> },
  {
    path: "/",
    element: (
      <ProtectedRoute>
        <AppLayout />
      </ProtectedRoute>
    ),
    errorElement: <NotFoundPage />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: "dashboard", element: <DashboardPage /> },
      { path: "schemes", element: <SchemesPage /> },
      { path: "schemes/:schemeId", element: <SchemeDetailPage /> },
      { path: "saved", element: <SavedSchemesPage /> },
      { path: "applications", element: <ApplicationsPage /> },
      { path: "chatbot", element: <ChatbotPage /> },
      { path: "profile", element: <ProfilePage /> },
      { path: "admin", element: <AdminPage /> }
    ]
  }
]);
