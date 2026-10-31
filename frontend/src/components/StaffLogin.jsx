import {
  LockKeyhole,
} from "lucide-react";

import {
  useState,
} from "react";

import {
  api,
} from "../services/api";


export default function StaffLogin({
  onLogin,
}) {

  const [
    email,
    setEmail,
  ] = useState("");


  const [
    password,
    setPassword,
  ] = useState("");


  const [
    loading,
    setLoading,
  ] = useState(false);


  const [
    error,
    setError,
  ] = useState("");


  async function handleSubmit(
    event
  ) {

    event.preventDefault();

    setError("");

    setLoading(true);


    try {

      const result =
        await api.login(
          email,
          password
        );


      api.setAuthToken(
        result.access_token
      );


      onLogin(
        result.staff
      );

    } catch (err) {

      setError(
        err.message
      );

    } finally {

      setLoading(false);

    }
  }


  return (

    <section
      className="panel"
      style={{
        maxWidth: "460px",
        margin: "48px auto",
        padding: "32px",
      }}
    >

      <div
        style={{
          display: "flex",
          gap: "12px",
          alignItems: "center",
          marginBottom: "24px",
        }}
      >

        <div className="brand-mark">
          <LockKeyhole
            size={20}
          />
        </div>

        <div>

          <span className="eyebrow">
            Staff only
          </span>

          <h2
            style={{
              margin: "4px 0 0",
            }}
          >
            Staff Login
          </h2>

        </div>

      </div>


      <p
        style={{
          marginBottom: "24px",
          opacity: 0.75,
        }}
      >
        Sign in to access bookings,
        guest information, room inventory,
        and service requests.
      </p>


      {
        error && (

          <div
            className="error-banner"
            style={{
              marginBottom: "16px",
            }}
          >
            {error}
          </div>

        )
      }


      <form
        onSubmit={
          handleSubmit
        }
        style={{
          display: "grid",
          gap: "18px",
        }}
      >

        <label
          style={{
            display: "grid",
            gap: "7px",
          }}
        >

          <span>
            Email
          </span>

          <input
            type="email"
            value={
              email
            }
            onChange={
              (event) =>
                setEmail(
                  event.target.value
                )
            }
            required
            autoComplete="username"
            style={{
              padding: "12px 14px",
              borderRadius: "10px",
              border:
                "1px solid #d7d7df",
              fontSize: "15px",
            }}
          />

        </label>


        <label
          style={{
            display: "grid",
            gap: "7px",
          }}
        >

          <span>
            Password
          </span>

          <input
            type="password"
            value={
              password
            }
            onChange={
              (event) =>
                setPassword(
                  event.target.value
                )
            }
            required
            autoComplete=
              "current-password"
            style={{
              padding: "12px 14px",
              borderRadius: "10px",
              border:
                "1px solid #d7d7df",
              fontSize: "15px",
            }}
          />

        </label>


        <button
          type="submit"
          className=
            "request-action-button"
          disabled={
            loading
          }
          style={{
            padding: "12px 16px",
          }}
        >

          {
            loading
              ? "Signing in..."
              : "Sign in"
          }

        </button>

      </form>

    </section>

  );
}