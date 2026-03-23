import { Navigate, Route, Routes } from "react-router-dom";
import { getToken } from "./api/client";
import ClientDetailPage from "./pages/ClientDetailPage";
import ClientsPage from "./pages/ClientsPage";
import LoginPage from "./pages/LoginPage";
import ScanDetailPage from "./pages/ScanDetailPage";

function Private({ children }: { children: React.ReactNode }) {
  if (!getToken()) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <div className="min-h-screen">
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <Private>
              <ClientsPage />
            </Private>
          }
        />
        <Route
          path="/clients/:clientId"
          element={
            <Private>
              <ClientDetailPage />
            </Private>
          }
        />
        <Route
          path="/scans/:scanId"
          element={
            <Private>
              <ScanDetailPage />
            </Private>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
