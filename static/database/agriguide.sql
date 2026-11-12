-- AgriGuide Database Schema (MySQL)
-- Import this file in phpMyAdmin / MySQL Workbench / XAMPP to set up the database.
-- Run: mysql -u root -p < agriguide.sql

CREATE DATABASE IF NOT EXISTS agriguide;
USE agriguide;

-- ============================
-- Users Table
-- ============================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('Farmer', 'Admin') DEFAULT 'Farmer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================
-- Crops Table
-- ============================
CREATE TABLE IF NOT EXISTS crops (
    id INT AUTO_INCREMENT PRIMARY KEY,
    crop_name VARCHAR(100) NOT NULL,
    soil_type VARCHAR(50) NOT NULL,
    season VARCHAR(50) NOT NULL,
    water_requirement VARCHAR(50) NOT NULL,
    notes VARCHAR(255)
);

-- ============================
-- Irrigation Table
-- ============================
CREATE TABLE IF NOT EXISTS irrigation (
    id INT AUTO_INCREMENT PRIMARY KEY,
    crop_name VARCHAR(100) NOT NULL,
    soil_condition VARCHAR(50) NOT NULL,
    rainfall VARCHAR(50) NOT NULL,
    recommendation VARCHAR(255) NOT NULL,
    tips TEXT
);

-- ============================
-- Fertilizer Table
-- ============================
CREATE TABLE IF NOT EXISTS fertilizer (
    id INT AUTO_INCREMENT PRIMARY KEY,
    crop_name VARCHAR(100) NOT NULL,
    soil_type VARCHAR(50) NOT NULL,
    nitrogen VARCHAR(50),
    phosphorus VARCHAR(50),
    potassium VARCHAR(50),
    notes TEXT
);

-- ============================
-- Diseases Table
-- ============================
CREATE TABLE IF NOT EXISTS diseases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    crop_name VARCHAR(100) NOT NULL,
    symptom VARCHAR(100) NOT NULL,
    disease_name VARCHAR(100) NOT NULL,
    disease_type VARCHAR(50),
    causes TEXT,
    prevention TEXT
);

-- ============================
-- Sample Seed Data
-- ============================
INSERT INTO crops (crop_name, soil_type, season, water_requirement, notes) VALUES
('Cotton', 'Black Soil', 'Kharif', 'Medium', 'High yield in black soil, good for Kharif season.'),
('Soybean', 'Black Soil', 'Kharif', 'Medium', 'Suitable for medium water availability.'),
('Groundnut', 'Black Soil', 'Kharif', 'Low', 'Grows well in black soil with moderate water.'),
('Wheat', 'Loamy Soil', 'Rabi', 'Medium', 'Best suited for cool weather and loamy soil.'),
('Rice', 'Clay Soil', 'Kharif', 'High', 'Requires standing water, ideal for clay soil.'),
('Sugarcane', 'Loamy Soil', 'Kharif', 'High', 'Long duration crop needing high water.'),
('Mustard', 'Sandy Soil', 'Rabi', 'Low', 'Drought-tolerant, grows in sandy soil.'),
('Maize', 'Red Soil', 'Kharif', 'Medium', 'Adapts well to red soil with moderate rainfall.');

INSERT INTO irrigation (crop_name, soil_condition, rainfall, recommendation, tips) VALUES
('Rice', 'Dry', 'No Rain', 'Watering is Recommended', 'Avoid overwatering.|Use drip or sprinkler if possible.|Check soil moisture regularly.'),
('Rice', 'Normal', 'Moderate Rain', 'Moderate Watering Advised', 'Water every alternate day.|Monitor field for waterlogging.'),
('Rice', 'Wet', 'Heavy Rain', 'No Watering Required', 'Ensure proper drainage.|Avoid irrigation until soil dries.'),
('Wheat', 'Dry', 'No Rain', 'Watering is Recommended', 'Irrigate early morning or evening.|Use mulching to retain moisture.'),
('Cotton', 'Dry', 'No Rain', 'Watering is Recommended', 'Deep watering once a week.|Check for pest activity during dry spells.');

INSERT INTO fertilizer (crop_name, soil_type, nitrogen, phosphorus, potassium, notes) VALUES
('Cotton', 'Black Soil', '60-80 kg/ha', '40-60 kg/ha', '40-50 kg/ha', 'Apply fertilizer based on soil test results.|Use organic matter for better soil health.'),
('Rice', 'Clay Soil', '80-100 kg/ha', '30-40 kg/ha', '30-40 kg/ha', 'Split nitrogen application into 3 doses.|Add organic manure before transplanting.'),
('Wheat', 'Loamy Soil', '100-120 kg/ha', '50-60 kg/ha', '40-50 kg/ha', 'Apply full phosphorus and potassium at sowing.|Top-dress nitrogen after first irrigation.');

INSERT INTO diseases (crop_name, symptom, disease_name, disease_type, causes, prevention) VALUES
('Tomato', 'Yellow Leaves', 'Early Blight', 'Fungal Disease', 'Excess moisture|Poor air circulation|Fungal infection', 'Remove affected leaves|Maintain proper spacing|Use disease-free seeds'),
('Tomato', 'Brown Spots', 'Septoria Leaf Spot', 'Fungal Disease', 'High humidity|Overcrowded planting|Water splashing on leaves', 'Rotate crops yearly|Avoid overhead watering|Apply fungicide if needed'),
('Cotton', 'Wilting', 'Fusarium Wilt', 'Fungal Disease', 'Soil-borne fungus|Poor drainage|Continuous cropping', 'Use resistant varieties|Practice crop rotation|Improve field drainage'),
('Rice', 'Leaf Blast Spots', 'Rice Blast', 'Fungal Disease', 'High nitrogen use|Humid weather|Dense planting', 'Use resistant varieties|Avoid excess nitrogen|Ensure good field drainage');

-- Default Admin account (password: admin123, hashed in the app on first run instead)
-- Managed by the Flask app's init_db() function, not inserted here.
