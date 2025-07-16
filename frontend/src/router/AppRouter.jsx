import { Routes, Route } from "react-router-dom";
import { routes } from "./routes";
import ProtectedRoute from "@/components/ProtectedRoute";
import Layout from "@/components/Layout";
import ErrorPage from "@/pages/Error";
import Home from "@/pages/Home";
import Admin from "@/pages/Admin";

const elementMap = {
  Home: <Home />,
  Admin: <Admin />,
};

export default function AppRouter() {
  return (
    <Routes>
      {routes.map(route => (
        <Route
          key={route.path}
          path={route.path}
          element={
            <ProtectedRoute permissionKey={route.permission}>
              <Layout>
                {elementMap[route.element]}
              </Layout>
            </ProtectedRoute>
          }
        />
      ))}
      <Route path="*" element={<Layout><ErrorPage code={404} /></Layout>} />
    </Routes>
  );
}