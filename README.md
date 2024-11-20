# Feedback App

A modern web application for requesting and managing feedback, built with Flask and PostgreSQL.

## Features

- **User Authentication**
  - Email verification system
  - Secure password handling
  - Profile management
  
- **User Profiles**
  - Customizable user profiles with first/last name
  - Company and role information
  - Password change functionality
  
- **Feedback Management**
  - Request feedback from peers
  - Track feedback requests
  - Modern dashboard interface

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Authentication**: Flask-Login
- **Email**: SendGrid
- **Frontend**: Bootstrap 5, HTML5, JavaScript
- **CSS Framework**: Bootstrap 5
- **Icons**: Bootstrap Icons

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/nstick13/feedback.git
   cd feedback
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   FLASK_APP=run.py
   FLASK_ENV=development
   DATABASE_URL=postgresql://postgres:@localhost/feedback_app
   SENDGRID_API_KEY=your_sendgrid_api_key
   SENDGRID_VERIFICATION_TEMPLATE_ID=your_template_id
   ```

5. Initialize the database:
   ```bash
   flask db upgrade
   ```

6. Run the application:
   ```bash
   flask run
   ```

## Database Migrations

To create a new migration after modifying models:
```bash
flask db migrate -m "Description of changes"
flask db upgrade
```

## Testing

Run tests using:
```bash
python -m pytest
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Flask documentation and community
- Bootstrap team for the excellent UI framework
- SendGrid for email services
