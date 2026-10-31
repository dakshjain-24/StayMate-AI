from collections import defaultdict
from datetime import date, timedelta, datetime, timezone
import json
from pathlib import Path

from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.models import Booking, Guest, RequestStatus, RequestType, ServiceRequest
from app.services.hotel_service import (
    cancel_booking,
    create_booking,
    create_service_request,
    extend_booking,
    find_available_rooms,
)


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "evaluation" / "operations_results.json"

TEST_CYCLES = 20
KEEP_TEST_DATA = False


def main():
    total = 0
    passed = 0

    category_total = defaultdict(int)
    category_passed = defaultdict(int)

    booking_ids = []
    request_ids = []
    test_emails = []

    failures = []

    def record(category: str, success: bool, description: str):
        nonlocal total, passed

        total += 1
        category_total[category] += 1

        if success:
            passed += 1
            category_passed[category] += 1
            print(f"[PASS] {description}")
        else:
            failures.append(description)
            print(f"[FAIL] {description}")

    with SessionLocal() as db:

        for i in range(TEST_CYCLES):

            print()
            print(
                f"========== TEST CYCLE "
                f"{i + 1}/{TEST_CYCLES} =========="
            )

            start = date(2027, 1, 10) + timedelta(
                days=i * 4
            )

            end = start + timedelta(days=2)
            extended_end = end + timedelta(days=1)

            email = (
                f"staymate_test_{i + 1}"
                f"@example.com"
            )

            guest_name = (
                f"StayMate Test Guest {i + 1}"
            )

            test_emails.append(email)

            # ---------------------------------
            # 1. Availability before booking
            # ---------------------------------

            rooms = find_available_rooms(
                db,
                hotel_id=1,
                room_type="deluxe",
                check_in=start,
                check_out=end,
            )

            record(
                "availability_before_booking",
                len(rooms) > 0,
                (
                    f"Availability check "
                    f"{start} -> {end}"
                ),
            )

            # ---------------------------------
            # 2. Create booking
            # ---------------------------------

            booking = create_booking(
                db,
                hotel_id=1,
                guest_name=guest_name,
                guest_email=email,
                room_type="deluxe",
                check_in=start,
                check_out=end,
            )

            booking_success = booking is not None

            record(
                "booking_creation",
                booking_success,
                f"Create booking for {email}",
            )

            if not booking:
                # We cannot extend or cancel something
                # that was not created.
                record(
                    "booking_extension",
                    False,
                    (
                        f"Extend booking for {email} "
                        f"(booking creation failed)"
                    ),
                )

                record(
                    "booking_cancellation",
                    False,
                    (
                        f"Cancel booking for {email} "
                        f"(booking creation failed)"
                    ),
                )

            else:
                booking_ids.append(booking.id)

                # ---------------------------------
                # 3. Extend booking
                # ---------------------------------

                extended_booking, result = (
                    extend_booking(
                        db,
                        booking_id=booking.id,
                        guest_email=email,
                        new_check_out=extended_end,
                    )
                )

                extension_success = (
                    result == "extended"
                    and extended_booking is not None
                    and extended_booking.check_out
                    == extended_end
                )

                record(
                    "booking_extension",
                    extension_success,
                    (
                        f"Extend booking "
                        f"#{booking.id} until "
                        f"{extended_end}"
                    ),
                )

                # ---------------------------------
                # 4. Cancel booking
                # ---------------------------------

                cancelled = cancel_booking(
                    db,
                    booking_id=booking.id,
                    guest_email=email,
                )

                record(
                    "booking_cancellation",
                    cancelled,
                    (
                        f"Cancel booking "
                        f"#{booking.id}"
                    ),
                )

            # ---------------------------------
            # 5. Availability after cancellation
            # ---------------------------------

            rooms_after_cancel = find_available_rooms(
                db,
                hotel_id=1,
                room_type="deluxe",
                check_in=start,
                check_out=extended_end,
            )

            record(
                "availability_after_cancellation",
                len(rooms_after_cancel) > 0,
                (
                    "Room availability restored "
                    f"after cancellation "
                    f"{start} -> {extended_end}"
                ),
            )

            # ---------------------------------
            # 6. Service request
            # ---------------------------------

            if i % 2 == 0:
                request_type = (
                    RequestType.housekeeping
                )

                description = (
                    "[E2E TEST] Please send two "
                    "extra towels."
                )

            else:
                request_type = (
                    RequestType.maintenance
                )

                description = (
                    "[E2E TEST] The AC is not "
                    "cooling properly."
                )

            service_request = (
                create_service_request(
                    db,
                    hotel_id=1,
                    request_type=request_type,
                    description=description,
                    room_number="301",
                )
            )

            request_success = (
                service_request is not None
                and service_request.status
                == RequestStatus.open
            )

            record(
                "service_request",
                request_success,
                (
                    f"Create "
                    f"{request_type.value} request"
                ),
            )

            if service_request:
                request_ids.append(
                    service_request.id
                )

        # ---------------------------------
        # Generate result
        # ---------------------------------

        success_rate = (
            passed / total * 100
            if total
            else 0.0
        )

        category_results = {}

        for category in category_total:
            ct = category_total[category]
            cp = category_passed[category]

            category_results[category] = {
                "passed": cp,
                "total": ct,
                "success_rate": round(
                    cp / ct * 100,
                    2,
                ),
            }

        report = {
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "test_cycles": TEST_CYCLES,
            "total_operations": total,
            "successful_operations": passed,
            "failed_operations": total - passed,
            "success_rate": round(
                success_rate,
                2,
            ),
            "categories": category_results,
            "failures": failures,
        }

        REPORT_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        REPORT_PATH.write_text(
            json.dumps(
                report,
                indent=2,
            ),
            encoding="utf-8",
        )

        # ---------------------------------
        # Cleanup test data
        # ---------------------------------

        if not KEEP_TEST_DATA:

            if request_ids:
                db.execute(
                    delete(ServiceRequest)
                    .where(
                        ServiceRequest.id.in_(
                            request_ids
                        )
                    )
                )

            if booking_ids:
                db.execute(
                    delete(Booking)
                    .where(
                        Booking.id.in_(
                            booking_ids
                        )
                    )
                )

            if test_emails:
                guest_ids = list(
                    db.scalars(
                        select(Guest.id)
                        .where(
                            Guest.email.in_(
                                test_emails
                            )
                        )
                    ).all()
                )

                if guest_ids:
                    db.execute(
                        delete(Guest)
                        .where(
                            Guest.id.in_(
                                guest_ids
                            )
                        )
                    )

            db.commit()

    print()
    print("=" * 60)
    print("STAYMATE OPERATIONAL WORKFLOW TEST")
    print("=" * 60)

    print(
        f"Test cycles: {TEST_CYCLES}"
    )

    print(
        f"Total operations: {total}"
    )

    print(
        f"Successful operations: {passed}"
    )

    print(
        f"Failed operations: {total - passed}"
    )

    print(
        f"Workflow success rate: "
        f"{success_rate:.1f}%"
    )

    print()
    print("Category results:")

    for category, result in category_results.items():
        print(
            f"- {category}: "
            f"{result['passed']}/"
            f"{result['total']} "
            f"({result['success_rate']:.1f}%)"
        )

    print()
    print(
        f"Report saved to: "
        f"{REPORT_PATH}"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()