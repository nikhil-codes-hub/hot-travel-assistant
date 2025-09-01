# Customer Travel Dataset

## Files in this directory:

- `customer_travel_dataset_sample.csv` - Sample of the full dataset (20 records) for demonstration
- `customer_travel_dataset.csv` - Full dataset with 30,000 customer travel records (**NOT included in Git**)

## Full Dataset Structure

The complete dataset contains 30,000 customer travel records with the following columns:
- `Traveler_Id` - Unique customer identifier
- `Traveler_name` - Customer name
- `Traveler_age` - Customer age
- `Nationality` - Customer nationality  
- `email_id` - Customer email address (for email-based lookup)
- `Departure_airport` - Origin airport
- `Departure_location` - Origin city
- `Departure_date` - Travel departure date
- `Destination_airport` - Destination airport
- `Destination_location` - Destination city
- `Booking_date` - When booking was made
- `Booking_id` - Unique booking identifier
- `Cabin_class` - Flight class (Economy/Business/First)

## Usage

The full dataset is generated using the `add_emails.py` script and is used by the UserProfileAgent for:
- Email-based customer lookup
- Travel history analysis
- Personalized recommendations
- Loyalty tier determination

## Sample Email Addresses for Testing

The system includes these test email addresses:
- henry.thomas596@yahoo.com (Gold tier, 29 bookings)
- amelia.martinez810@gmail.com (Gold tier, 28 bookings) 
- noah.smith754@icloud.com (Gold tier, 25 bookings)

## Note

The full 30K dataset is excluded from Git due to size. Use the sample dataset for development and testing, or regenerate the full dataset using the provided scripts.