import {
  Hotel,
  LayoutDashboard,
  LockKeyhole,
  LogOut,
  MessageSquareText,
} from "lucide-react";

import {
  useEffect,
  useState,
} from "react";

import ChatPanel from "./components/ChatPanel";
import StaffLogin from "./components/StaffLogin";
import Dashboard from "./pages/Dashboard";

import {
  api,
} from "./services/api";


export default function App() {
  const [
    view,
    setView,
  ] = useState("chat");

  const [
    staff,
    setStaff,
  ] = useState(null);

  const [
    checkingAuth,
    setCheckingAuth,
  ] = useState(true);


  useEffect(() => {
    async function restoreSession() {
      if (!api.getAuthToken()) {
        setCheckingAuth(false);
        return;
      }

      try {
        const staffData =
          await api.me();

        setStaff(staffData);
      } catch {
        api.clearAuthToken();
        setStaff(null);
      } finally {
        setCheckingAuth(false);
      }
    }

    restoreSession();
  }, []);


  function handleStaffLogin(
    staffData
  ) {
    setStaff(staffData);
    setView("dashboard");
  }


  function logout() {
    api.clearAuthToken();

    setStaff(null);
    setView("chat");
  }


  function openDashboard() {
    if (staff) {
      setView("dashboard");
      return;
    }

    setView("staff-login");
  }


  if (checkingAuth) {
    return (
      <div className="app-shell">
        <main className="main-content">
          <section
            className="panel"
            style={{
              margin: "48px",
              padding: "32px",
            }}
          >
            Checking staff session...
          </section>
        </main>
      </div>
    );
  }


  return (
    <div className="app-shell">

      <aside className="sidebar">

        <div className="brand">

          <div className="brand-mark">
            <Hotel size={22} />
          </div>

          <div>
            <strong>
              StayMate AI
            </strong>

            <span>
              Hotel Operations
            </span>
          </div>

        </div>


        <nav>

          <button
            className={
              view === "chat"
                ? "active"
                : ""
            }
            onClick={() =>
              setView("chat")
            }
          >
            <MessageSquareText
              size={18}
            />

            AI Receptionist
          </button>


          <button
            className={
              (
                view === "dashboard"
                ||
                view === "staff-login"
              )
                ? "active"
                : ""
            }
            onClick={
              openDashboard
            }
          >

            {
              staff
                ? (
                  <LayoutDashboard
                    size={18}
                  />
                )
                : (
                  <LockKeyhole
                    size={18}
                  />
                )
            }

            {
              staff
                ? "Staff Dashboard"
                : "Staff Login"
            }

          </button>


          {
            staff && (
              <button
                onClick={
                  logout
                }
              >
                <LogOut
                  size={18}
                />

                Sign out
              </button>
            )
          }

        </nav>


        <div className="sidebar-note">

          <span>
            Demo property
          </span>

          <strong>
            StayMate Grand
          </strong>

          <small>
            Varanasi, India
          </small>

        </div>

      </aside>


      <main className="main-content">

        <header className="topbar">

          <div>

            <span className="eyebrow">
              Agentic hotel operations assistant
            </span>

            <h1>
              {
                view === "dashboard"
                  ? "Staff Dashboard"
                  : view === "staff-login"
                    ? "Staff Access"
                    : "AI Receptionist"
              }
            </h1>

          </div>


          <div className="profile">
            {
              staff
                ? (
                  staff.name
                    ?.charAt(0)
                    ?.toUpperCase()
                  || "S"
                )
                : "AI"
            }
          </div>

        </header>


        {
          view === "dashboard"
          && staff
            ? (
              <Dashboard />
            )

            : view === "staff-login"
              ? (
                <StaffLogin
                  onLogin={
                    handleStaffLogin
                  }
                />
              )

              : (
                <ChatPanel />
              )
        }

      </main>

    </div>
  );
}