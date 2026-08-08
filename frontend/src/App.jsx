import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import NavBar from "./components/NavBar";
import ProtectedRoute from "./components/ProtectedRoute";
import AdminRoute from "./components/AdminRoute";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import UserHome from "./pages/UserHome";
import AdminUpload from "./pages/AdminUpload";
import AdminReview from "./pages/AdminReview";
import AdminHistory from "./pages/AdminHistory";
import MeetingDetail from "./pages/MeetingDetail";

function Home() {
  const { isAdmin } = useAuth();
  return isAdmin ? <Navigate to="/admin/upload" replace /> : <UserHome />;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <NavBar />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />

          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<Home />} />

            <Route element={<AdminRoute />}>
              <Route path="/admin/upload" element={<AdminUpload />} />
              <Route path="/admin/review/:threadId" element={<AdminReview />} />
              <Route path="/admin/history" element={<AdminHistory />} />
              <Route path="/admin/meetings/:meetingId" element={<MeetingDetail />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
