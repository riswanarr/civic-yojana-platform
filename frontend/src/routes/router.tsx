import { createBrowserRouter } from "react-router-dom";
import { AppLayout } from "@/layouts/AppLayout";
import { AdminPage } from "@/pages/AdminPage";
import { ApplicationsPage } from "@/pages/ApplicationsPage";
import { ChatbotPage } from "@/pages/ChatbotPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { HomePage } from "@/pages/HomePage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { ProfilePage } from "@/pages/ProfilePage";
import { SavedSchemesPage } from "@/pages/SavedSchemesPage";
import { SchemeDetailPage } from "@/pages/SchemeDetailPage";
import { SchemesPage } from "@/pages/SchemesPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    errorElement: <NotFoundPage />,
    children: [
      { index: true, element: <HomePage /> },
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

