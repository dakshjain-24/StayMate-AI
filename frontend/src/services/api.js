const API_URL =
  import.meta.env.VITE_API_URL ||
  "http://localhost:8000/api";


const TOKEN_KEY =
  "staymate_staff_token";


function getAuthToken() {
  return sessionStorage.getItem(
    TOKEN_KEY
  );
}


function setAuthToken(token) {
  sessionStorage.setItem(
    TOKEN_KEY,
    token
  );
}


function clearAuthToken() {
  sessionStorage.removeItem(
    TOKEN_KEY
  );
}


async function request(
  path,
  options = {}
) {

  const token =
    getAuthToken();


  const response = await fetch(
    `${API_URL}${path}`,
    {
      ...options,

      headers: {
        "Content-Type":
          "application/json",

        ...(token
          ? {
              Authorization:
                `Bearer ${token}`,
            }
          : {}),

        ...(options.headers || {}),
      },
    }
  );


  if (!response.ok) {

    let message =
      "Something went wrong";


    try {

      const body =
        await response.json();

      message =
        body.detail ||
        message;

    } catch {
      // Keep generic message.
    }


    if (
      response.status === 401
      &&
      path !== "/auth/login"
    ) {
      clearAuthToken();
    }


    throw new Error(
      message
    );
  }


  return response.json();
}


export const api = {

  getAuthToken,

  setAuthToken,

  clearAuthToken,


  chat(
    message,
    threadId
  ) {

    return request(
      "/chat",
      {
        method: "POST",

        body: JSON.stringify(
          {
            message,
            thread_id:
              threadId,
            hotel_id: 1,
          }
        ),
      }
    );
  },


  login(
    email,
    password
  ) {

    return request(
      "/auth/login",
      {
        method: "POST",

        body: JSON.stringify(
          {
            email,
            password,
          }
        ),
      }
    );
  },


  me() {
    return request(
      "/auth/me"
    );
  },


  stats() {
    return request(
      "/dashboard/stats"
    );
  },


  rooms() {
    return request(
      "/rooms"
    );
  },


  bookings() {
    return request(
      "/bookings"
    );
  },


  serviceRequests() {
    return request(
      "/service-requests"
    );
  },


  updateServiceRequestStatus(
    requestId,
    status
  ) {

    return request(
      `/service-requests/${requestId}/status`,
      {
        method: "PATCH",

        body: JSON.stringify(
          {
            status,
          }
        ),
      }
    );
  },
};