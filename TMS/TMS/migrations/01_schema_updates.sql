-- Migration Script: Phase 1 & 2 Schema Updates
-- Instructions: Run these queries on your local MySQL database.

-- 1. Ensure `Role` column in `users` table can accept the new 'customer' role.
-- (Assuming Role was a VARCHAR or an ENUM. This modifies it to an ENUM for safety, or updates existing ENUM)
ALTER TABLE users MODIFY COLUMN Role ENUM('admin', 'manager', 'accountant', 'driver', 'customer') NOT NULL;

-- 2. Add Unique Constraints for validation
ALTER TABLE users ADD UNIQUE INDEX idx_unique_email (Email);
ALTER TABLE vehicles ADD UNIQUE INDEX idx_unique_truck_no (Truck_Number);
ALTER TABLE vehicles ADD UNIQUE INDEX idx_unique_reg_no (Registration_Number);

-- 3. Create the `bookings` table for the Customer Booking System (Phase 2 & 4 prep)
CREATE TABLE IF NOT EXISTS bookings (
    booking_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    pickup_location VARCHAR(255) NOT NULL,
    drop_location VARCHAR(255) NOT NULL,
    package_type VARCHAR(100) NOT NULL,
    package_weight DECIMAL(10,2) NOT NULL,
    delivery_date DATE NOT NULL,
    contact_info VARCHAR(255) NOT NULL,
    status ENUM('Pending', 'Approved', 'Assigned', 'In Transit', 'Delivered', 'Cancelled') DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 4. Update `trips` table to align tracking statuses
ALTER TABLE trips MODIFY COLUMN Status ENUM('Pending', 'Approved', 'Assigned', 'In Transit', 'Delivered', 'Cancelled') DEFAULT 'Pending';

-- 5. Add booking_id to trips to link trips with bookings
ALTER TABLE trips ADD COLUMN booking_id INT NULL;
ALTER TABLE trips ADD FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE SET NULL;
