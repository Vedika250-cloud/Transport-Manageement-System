-- Migration Script 02: Add Constraints & Foreign Keys
-- Ensure to run this AFTER 01_schema_updates.sql has been applied

USE transport_management;

-- 1. Ensure driver references are valid before adding constraint
DELETE FROM trips WHERE Driver_id NOT IN (SELECT driver_id FROM drivers);
ALTER TABLE trips
    ADD CONSTRAINT fk_trips_driver
    FOREIGN KEY (Driver_id) REFERENCES drivers(driver_id)
    ON DELETE SET NULL
    ON UPDATE CASCADE;

-- 2. Ensure vehicle references are valid before adding constraint
DELETE FROM trips WHERE Vehicle_id NOT IN (SELECT Vehicle_id FROM vehicles);
ALTER TABLE trips
    ADD CONSTRAINT fk_trips_vehicle
    FOREIGN KEY (Vehicle_id) REFERENCES vehicles(Vehicle_id)
    ON DELETE SET NULL
    ON UPDATE CASCADE;

-- 3. Ensure booking references to customers are valid
DELETE FROM bookings WHERE customer_id NOT IN (SELECT user_id FROM users);
ALTER TABLE bookings
    ADD CONSTRAINT fk_bookings_customer
    FOREIGN KEY (customer_id) REFERENCES users(user_id)
    ON DELETE CASCADE
    ON UPDATE CASCADE;

-- 4. Ensure consignment trip references are valid
DELETE FROM consignments WHERE trip_id NOT IN (SELECT Trip_id FROM trips);
ALTER TABLE consignments
    ADD CONSTRAINT fk_consignments_trip
    FOREIGN KEY (trip_id) REFERENCES trips(Trip_id)
    ON DELETE CASCADE
    ON UPDATE CASCADE;

-- 5. Payments referential integrity
-- Some legacy databases might have missing bookings/consignments. Clean them up or ignore.
-- First, if Payments have a Consignment_id:
DELETE FROM payments WHERE Consignment_id IS NOT NULL AND Consignment_id NOT IN (SELECT Consignments_id FROM consignments);
ALTER TABLE payments
    ADD CONSTRAINT fk_payments_consignment
    FOREIGN KEY (Consignment_id) REFERENCES consignments(Consignments_id)
    ON DELETE SET NULL
    ON UPDATE CASCADE;

-- If Payments have a Booking_id (if we added it):
-- DELETE FROM payments WHERE Booking_id IS NOT NULL AND Booking_id NOT IN (SELECT booking_id FROM bookings);
-- ALTER TABLE payments
--     ADD CONSTRAINT fk_payments_booking
--     FOREIGN KEY (Booking_id) REFERENCES bookings(booking_id)
--     ON DELETE SET NULL
--     ON UPDATE CASCADE;

-- 6. Add Indexes for optimization
CREATE INDEX idx_trips_status ON trips(Status);
CREATE INDEX idx_trips_dates ON trips(Start_Date, End_Date);
CREATE INDEX idx_bookings_status ON bookings(status);
CREATE INDEX idx_users_role ON users(Role);
