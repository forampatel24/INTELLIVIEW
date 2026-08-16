-- Add focus_skills JSON column to domains
ALTER TABLE domains
    ADD COLUMN focus_skills JSON NULL AFTER description;