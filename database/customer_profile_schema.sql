-- Customer Profile Database Schema
-- This schema stores customer travel history and preferences for personalized recommendations

-- Customer Profile Table
CREATE TABLE IF NOT EXISTS customer_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),
    preferred_language VARCHAR(10) DEFAULT 'en',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email)
);

-- Customer Travel History Table
CREATE TABLE IF NOT EXISTS customer_travel_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_email VARCHAR(255) NOT NULL,
    destination VARCHAR(200) NOT NULL,
    country VARCHAR(100),
    city VARCHAR(100),
    event_name VARCHAR(200),
    event_type VARCHAR(100), -- e.g., 'festival', 'conference', 'leisure', 'business'
    travel_date_start DATE,
    travel_date_end DATE,
    season VARCHAR(20), -- e.g., 'spring', 'summer', 'monsoon', 'winter'
    budget_range VARCHAR(50), -- e.g., 'budget', 'mid-range', 'luxury'
    travel_style VARCHAR(100), -- e.g., 'solo', 'family', 'group', 'couple'
    satisfaction_rating INT DEFAULT NULL, -- 1-5 scale
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_email) REFERENCES customer_profiles(email) ON DELETE CASCADE,
    INDEX idx_customer_email (customer_email),
    INDEX idx_event_type (event_type),
    INDEX idx_travel_date (travel_date_start),
    INDEX idx_destination (destination)
);

-- Customer Preferences Table
CREATE TABLE IF NOT EXISTS customer_preferences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_email VARCHAR(255) NOT NULL,
    preference_type VARCHAR(100) NOT NULL, -- e.g., 'accommodation', 'transport', 'activity', 'cuisine'
    preference_value VARCHAR(200) NOT NULL,
    weight INT DEFAULT 1, -- Higher weight = stronger preference
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_email) REFERENCES customer_profiles(email) ON DELETE CASCADE,
    INDEX idx_customer_email (customer_email),
    INDEX idx_preference_type (preference_type)
);

-- Event Calendar Table (for upcoming events to recommend)
CREATE TABLE IF NOT EXISTS event_calendar (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_name VARCHAR(200) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    destination VARCHAR(200) NOT NULL,
    country VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    event_date_start DATE NOT NULL,
    event_date_end DATE,
    description TEXT,
    season VARCHAR(20),
    similar_events TEXT, -- JSON array of similar event types
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_event_type (event_type),
    INDEX idx_destination (destination),
    INDEX idx_event_date (event_date_start),
    INDEX idx_country_city (country, city)
);

-- Sample Data for Testing
INSERT IGNORE INTO customer_profiles (email, first_name, last_name) VALUES 
('john.doe@example.com', 'John', 'Doe'),
('jane.smith@example.com', 'Jane', 'Smith');

INSERT IGNORE INTO customer_travel_history (customer_email, destination, country, city, event_name, event_type, travel_date_start, travel_date_end, season, travel_style) VALUES 
('john.doe@example.com', 'Bangalore, India', 'India', 'Bangalore', 'Diwali Festival', 'festival', '2023-11-12', '2023-11-15', 'post-monsoon', 'family'),
('john.doe@example.com', 'Munich, Germany', 'Germany', 'Munich', 'Oktoberfest', 'festival', '2023-09-20', '2023-09-25', 'autumn', 'group'),
('jane.smith@example.com', 'Rajasthan, India', 'India', 'Jaipur', 'Holi Festival', 'festival', '2023-03-08', '2023-03-10', 'spring', 'couple');

INSERT IGNORE INTO event_calendar (event_name, event_type, destination, country, city, event_date_start, event_date_end, description, season, similar_events) VALUES 
('Dussehra Festival', 'festival', 'Mysore, India', 'India', 'Mysore', '2024-10-24', '2024-10-24', 'Grand Dussehra celebration in the royal city of Mysore', 'post-monsoon', '["Diwali", "Navratri", "Durga Puja"]'),
('Christmas Markets', 'festival', 'Vienna, Austria', 'Austria', 'Vienna', '2024-12-01', '2024-12-24', 'Traditional Christmas markets with mulled wine and crafts', 'winter', '["Oktoberfest", "Winter festivals", "Christmas celebrations"]'),
('Holi Festival', 'festival', 'Mathura, India', 'India', 'Mathura', '2024-03-25', '2024-03-25', 'The original Holi celebration in Krishna\'s birthplace', 'spring', '["Diwali", "Dussehra", "Color festivals"]'),
('Cherry Blossom Festival', 'festival', 'Tokyo, Japan', 'Japan', 'Tokyo', '2024-04-01', '2024-04-15', 'Beautiful cherry blossom season in Tokyo', 'spring', '["Spring festivals", "Nature festivals", "Cultural events"]');