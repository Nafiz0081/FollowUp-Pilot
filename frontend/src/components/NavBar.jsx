import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function NavBar() {
  const { user, profile, isAdmin, signOut } = useAuth();
  const navigate = useNavigate();

  const handleSignOut = async () => {
    await signOut();
    navigate("/login");
  };

  return (
    <nav className="navbar">
      <Link to="/" className="navbar-brand">
        FollowUp Pilot
      </Link>
      <div className="navbar-links">
        {user && isAdmin && (
          <>
            <Link to="/admin/upload">Upload meeting</Link>
            <Link to="/admin/history">History</Link>
          </>
        )}
        {user && !isAdmin && <Link to="/">My tasks</Link>}
        {user ? (
          <>
            <span className="navbar-user">{profile?.name || user.email}</span>
            <button className="btn btn-ghost" onClick={handleSignOut}>
              Sign out
            </button>
          </>
        ) : (
          <>
            <Link to="/login">Log in</Link>
            <Link to="/signup">Sign up</Link>
          </>
        )}
      </div>
    </nav>
  );
}
