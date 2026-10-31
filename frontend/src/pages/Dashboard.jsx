import {
  useEffect,
  useState,
} from "react";

import {
  RefreshCw,
} from "lucide-react";

import {
  api,
} from "../services/api";

import StatCard from "../components/StatCard";


export default function Dashboard() {

  const [
    stats,
    setStats,
  ] = useState(null);

  const [
    rooms,
    setRooms,
  ] = useState([]);

  const [
    bookings,
    setBookings,
  ] = useState([]);

  const [
    requests,
    setRequests,
  ] = useState([]);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    updatingRequestId,
    setUpdatingRequestId,
  ] = useState(null);

  const [
    error,
    setError,
  ] = useState("");


  async function loadDashboard() {

    setLoading(true);

    setError("");

    try {

      const [
        statsData,
        roomData,
        bookingData,
        requestData,
      ] = await Promise.all([
        api.stats(),
        api.rooms(),
        api.bookings(),
        api.serviceRequests(),
      ]);

      setStats(
        statsData
      );

      setRooms(
        roomData
      );

      setBookings(
        bookingData
      );

      setRequests(
        requestData
      );

    } catch (err) {

      setError(
        err.message
      );

    } finally {

      setLoading(false);

    }

  }


  async function changeRequestStatus(
    requestId,
    status
  ) {

    setUpdatingRequestId(
      requestId
    );

    setError("");

    try {

      await api.updateServiceRequestStatus(
        requestId,
        status
      );

      const [
        statsData,
        requestData,
      ] = await Promise.all([
        api.stats(),
        api.serviceRequests(),
      ]);

      setStats(
        statsData
      );

      setRequests(
        requestData
      );

    } catch (err) {

      setError(
        err.message
      );

    } finally {

      setUpdatingRequestId(
        null
      );

    }

  }


  useEffect(
    () => {
      loadDashboard();
    },
    []
  );


  return (

    <section className="dashboard">

      {/* ====================================
          DASHBOARD HEADER
      ==================================== */}

      <div className="dashboard-title-row">

        <div>

          <span className="eyebrow">
            Staff workspace
          </span>

          <h2>
            Operations Dashboard
          </h2>

        </div>


        <button
          className="secondary-button"
          onClick={
            loadDashboard
          }
          disabled={
            loading
          }
        >

          <RefreshCw
            size={16}
            className={
              loading
                ? "refreshing"
                : ""
            }
          />

          {
            loading
              ? "Refreshing..."
              : "Refresh"
          }

        </button>

      </div>


      {/* ERROR */}

      {
        error && (

          <div className="error-banner">
            {error}
          </div>

        )
      }


      {/* ====================================
          STATS
      ==================================== */}

      <div className="stats-grid">

        <StatCard
          label="Total rooms"
          value={
            stats?.total_rooms
          }
          note="Across the property"
        />


        <StatCard
          label="Available"
          value={
            stats?.available_rooms
          }
          note="Ready for guests"
        />


        <StatCard
          label="Active bookings"
          value={
            stats?.active_bookings
          }
          note="Confirmed + checked in"
        />


        <StatCard
          label="Open requests"
          value={
            stats?.open_service_requests
          }
          note="Needs staff attention"
        />

      </div>


      {/* ====================================
          MAIN DASHBOARD GRID
      ==================================== */}

      <div className="dashboard-grid">

        {/* ==================================
            BOOKINGS
        ================================== */}

        <div className="panel table-panel">

          <div className="panel-heading">

            <div>

              <span className="eyebrow">
                Reservations
              </span>

              <h3>
                Recent bookings
              </h3>

            </div>

          </div>


          <div className="table-wrap">

            <table>

              <thead>

                <tr>

                  <th>
                    Guest
                  </th>

                  <th>
                    Room
                  </th>

                  <th>
                    Stay
                  </th>

                  <th>
                    Status
                  </th>

                </tr>

              </thead>


              <tbody>

                {
                  bookings.map(
                    (booking) => (

                      <tr
                        key={
                          booking.id
                        }
                      >

                        <td>

                          <strong>
                            {
                              booking.guest_name
                            }
                          </strong>

                          <small>
                            {
                              booking.guest_email
                            }
                          </small>

                        </td>


                        <td>

                          {
                            booking.room_number
                          }

                          <small>
                            {
                              booking.room_type
                            }
                          </small>

                        </td>


                        <td>

                          {
                            booking.check_in
                          }

                          <small>
                            to{" "}
                            {
                              booking.check_out
                            }
                          </small>

                        </td>


                        <td>

                          <span
                            className={
                              `table-status ${booking.status}`
                            }
                          >

                            {
                              booking.status
                                .replaceAll(
                                  "_",
                                  " "
                                )
                            }

                          </span>

                        </td>

                      </tr>

                    )
                  )
                }


                {
                  !bookings.length &&
                  !loading && (

                    <tr>

                      <td
                        colSpan="4"
                      >
                        No bookings yet.
                      </td>

                    </tr>

                  )
                }

              </tbody>

            </table>

          </div>

        </div>


        {/* ==================================
            SERVICE REQUESTS
        ================================== */}

        <div className="panel request-panel">

          <div className="panel-heading">

            <div>

              <span className="eyebrow">
                Task queue
              </span>

              <h3>
                Service requests
              </h3>

            </div>

          </div>


          <div className="request-list">

            {
              requests.map(
                (item) => {

                  const isUpdating =
                    updatingRequestId ===
                    item.id;


                  return (

                    <article
                      className="request-item"
                      key={
                        item.id
                      }
                      data-type={
                        item.request_type
                      }
                    >

                      <div>

                        <strong>

                          {
                            item.request_type
                              .replaceAll(
                                "_",
                                " "
                              )
                          }

                        </strong>


                        <span>

                          {
                            item.room_number
                              ? `Room ${item.room_number}`
                              : "Front desk"
                          }

                        </span>

                      </div>


                      <p>
                        {
                          item.description
                        }
                      </p>


                      <div className="request-actions">

                        <span
                          className={
                            `request-status ${item.status}`
                          }
                        >

                          {
                            item.status
                              .replaceAll(
                                "_",
                                " "
                              )
                          }

                        </span>


                        {
                          item.status ===
                          "open" && (

                            <button
                              className="request-action-button"
                              disabled={
                                isUpdating
                              }
                              onClick={
                                () =>
                                  changeRequestStatus(
                                    item.id,
                                    "in_progress"
                                  )
                              }
                            >

                              {
                                isUpdating
                                  ? "Updating..."
                                  : "Start"
                              }

                            </button>

                          )
                        }


                        {
                          item.status ===
                          "in_progress" && (

                            <button
                              className="request-action-button complete"
                              disabled={
                                isUpdating
                              }
                              onClick={
                                () =>
                                  changeRequestStatus(
                                    item.id,
                                    "resolved"
                                  )
                              }
                            >

                              {
                                isUpdating
                                  ? "Updating..."
                                  : "Complete"
                              }

                            </button>

                          )
                        }

                      </div>

                    </article>

                  );

                }
              )
            }


            {
              !requests.length &&
              !loading && (

                <p className="empty-state">
                  No service requests.
                </p>

              )
            }

          </div>

        </div>

      </div>


      {/* ====================================
          ROOM INVENTORY
      ==================================== */}

      <div className="panel room-panel">

        <div className="panel-heading">

          <div>

            <span className="eyebrow">
              Inventory
            </span>

            <h3>
              Room overview
            </h3>

          </div>

        </div>


        <div className="room-grid">

          {
            rooms.map(
              (room) => (

                <article
                  className="room-card"
                  key={
                    room.id
                  }
                >

                  <div>

                    <strong>
                      {
                        room.number
                      }
                    </strong>

                    <span>
                      {
                        room.room_type
                      }
                    </span>

                  </div>


                  <span
                    className={
                      `room-status ${room.status}`
                    }
                  >

                    {
                      room.status
                    }

                  </span>


                  <small>

                    ₹
                    {
                      Math.round(
                        room.price_per_night
                      )
                        .toLocaleString(
                          "en-IN"
                        )
                    }{" "}

                    / night

                  </small>

                </article>

              )
            )
          }

        </div>

      </div>

    </section>

  );

}