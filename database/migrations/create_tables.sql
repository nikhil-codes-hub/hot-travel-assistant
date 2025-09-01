-- HOT Intelligent Travel Assistant MySQL Schema

CREATE DATABASE IF NOT EXISTS hot_travel_assistant 
DEFAULT CHARACTER SET utf8mb4 
DEFAULT COLLATE utf8mb4_unicode_ci;

USE hot_travel_assistant;

-- User Profiles Table
CREATE TABLE user_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id VARCHAR(255) UNIQUE NOT NULL,
    nationality CHAR(3),
    passport_number_hash VARCHAR(255),
    loyalty_tier VARCHAR(50),
    preferences JSON,
    travel_history JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_customer_id (customer_id)
);

-- Commercial Knowledge Base Table
CREATE TABLE commercial_knowledge_base (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rule_type VARCHAR(100) NOT NULL,
    supplier VARCHAR(100),
    category VARCHAR(100),
    conditions JSON,
    action JSON,
    priority INT DEFAULT 0,
    active BOOLEAN DEFAULT TRUE,
    effective_from DATETIME,
    effective_to DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_rule_type (rule_type),
    INDEX idx_supplier (supplier),
    INDEX idx_category (category),
    INDEX idx_active (active)
);

-- Search Sessions Table
CREATE TABLE search_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    customer_id VARCHAR(255),
    original_request TEXT,
    extracted_requirements JSON,
    search_results JSON,
    final_itinerary JSON,
    status VARCHAR(50) DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id),
    INDEX idx_customer_id (customer_id),
    INDEX idx_status (status)
);

-- Agent Executions Table
CREATE TABLE agent_executions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(255),
    agent_name VARCHAR(100) NOT NULL,
    input_data JSON,
    output_data JSON,
    execution_time_ms INT,
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES search_sessions(session_id) ON DELETE CASCADE,
    INDEX idx_session_id (session_id),
    INDEX idx_agent_name (agent_name),
    INDEX idx_status (status)
);

-- Destination Data Table
CREATE TABLE destination_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    destination_code VARCHAR(10) NOT NULL,
    destination_name VARCHAR(255) NOT NULL,
    country CHAR(3),
    seasonal_data JSON,
    budget_ranges JSON,
    family_friendly BOOLEAN DEFAULT FALSE,
    visa_required_countries JSON,
    health_requirements JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_destination_code (destination_code),
    INDEX idx_country (country),
    INDEX idx_family_friendly (family_friendly)
);